pipeline {
  agent any
  environment {
    IMAGE = "patient-api:${BUILD_NUMBER}"
    TRIVY_IMAGE_ARCHIVE = "patient-api-${BUILD_NUMBER}.tar"
    DAST_NETWORK = "patient-api-dast-${BUILD_NUMBER}"
    DAST_CONTAINER = "patient-api-dast-app-${BUILD_NUMBER}"
  }
  stages {
    stage('Checkout') {
      steps { checkout scm }
    }

    stage('1. Secret Scan') {
      steps {
        sh 'docker run --rm -v "$WORKSPACE:/repo" zricethezav/gitleaks:latest detect --source=/repo --no-git --exit-code 1'
      }
    }

    stage('2. SAST - Code Scan') {
      steps {
        sh 'docker run --rm -v "$WORKSPACE:/src" -w /src python:3.12-slim sh -c "pip install -q bandit && bandit -r app.py -ll"'
      }
    }

    stage('3. Dependency Scan') {
      steps {
        sh 'docker run --rm -v "$WORKSPACE:/src" -w /src python:3.12-slim sh -c "pip install -q pip-audit && pip-audit -r requirements.txt"'
      }
    }

    stage('4. Dockerfile Lint') {
      steps {
        sh 'docker run --rm -i hadolint/hadolint:latest < Dockerfile'
      }
    }

    stage('5. Build Image') {
      steps { sh 'docker build -t "$IMAGE" .' }
    }

    stage('6. Image Scan (Trivy)') {
      steps {
        sh '''
          docker save --output "$WORKSPACE/$TRIVY_IMAGE_ARCHIVE" "$IMAGE"
          docker run --rm -v "$WORKSPACE:/work" aquasec/trivy:latest image \
            --input "/work/$TRIVY_IMAGE_ARCHIVE" --severity HIGH,CRITICAL --exit-code 1 --ignore-unfixed
        '''
      }
    }

    stage('7. Deploy to Minikube') {
      steps {
        sh '''
          minikube image load "$IMAGE"
          sed "s/IMAGE_TAG/${BUILD_NUMBER}/" k8s/deployment.yaml | kubectl apply -f -
          kubectl -n healthcare rollout status deployment/patient-api --timeout=120s
        '''
      }
    }

    stage('8. DAST (OWASP ZAP)') {
      steps {
        sh '''
          docker network create "$DAST_NETWORK"
          docker run -d --rm --network "$DAST_NETWORK" --name "$DAST_CONTAINER" "$IMAGE"
          attempt=0
          until docker exec "$DAST_CONTAINER" python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health', timeout=1)" >/dev/null 2>&1; do
            attempt=$((attempt + 1))
            if [ "$attempt" -ge 30 ]; then
              echo "DAST target did not become ready" >&2
              exit 1
            fi
            sleep 1
          done
          docker run --rm --network "$DAST_NETWORK" -v "$WORKSPACE:/zap/wrk" ghcr.io/zaproxy/zaproxy:stable \
            zap-baseline.py -t "http://$DAST_CONTAINER:8080/health" -I
          docker run --rm --network "$DAST_NETWORK" -v "$WORKSPACE:/zap/wrk" ghcr.io/zaproxy/zaproxy:stable \
            zap-baseline.py -t "http://$DAST_CONTAINER:8080/patients" -I
        '''
      }
    }
  }
  post {
    always {
      sh 'docker stop "$DAST_CONTAINER" >/dev/null 2>&1 || true; docker network rm "$DAST_NETWORK" >/dev/null 2>&1 || true; rm -f "$WORKSPACE/$TRIVY_IMAGE_ARCHIVE"'
    }
  }
}
