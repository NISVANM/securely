pipeline {
  agent any

  environment {
    // Folders where Jenkins can find docker, kubectl, minikube, git (Mac)
    PATH = "/Users/niswa/.docker/bin:/opt/homebrew/bin:/usr/local/bin:${env.PATH}"

    IMAGE            = "patient-api:${BUILD_NUMBER}"
    MINIKUBE_PROFILE = "patient-api-calico"
    DAST_NET         = "patient-api-dast-${BUILD_NUMBER}"
    DAST_APP         = "patient-api-dast-app-${BUILD_NUMBER}"
    IMAGE_TAR        = "patient-api-${BUILD_NUMBER}.tar"
  }

  stages {

    stage('Checkout') {
      steps { checkout scm }
    }

    stage('1. Secret Scan') {
      steps {
        sh '''
          docker run --rm -v "$PWD":/repo zricethezav/gitleaks:latest \
            detect --source=/repo --no-git --exit-code 1
        '''
      }
    }

    stage('2. SAST - Code Scan') {
      steps {
        sh '''
          docker run --rm -v "$PWD":/src -w /src python:3.12-slim \
            sh -c "pip install -q bandit && bandit -r app.py -ll"
        '''
      }
    }

    stage('3. Dependency Scan') {
      steps {
        sh '''
          docker run --rm -v "$PWD":/src -w /src python:3.12-slim \
            sh -c "pip install -q pip-audit && pip-audit -r requirements.txt"
        '''
      }
    }

    stage('4. Dockerfile Lint') {
      steps {
        // Fails only on errors; warnings are printed so you can learn from them
        sh '''
          docker run --rm -i hadolint/hadolint \
            hadolint --failure-threshold error - < Dockerfile
        '''
      }
    }

    stage('5. Build Image') {
      steps {
        sh 'docker build --provenance=false --sbom=false -t "$IMAGE" .'
      }
    }

    stage('6. Image Scan (Trivy)') {
      steps {
        sh '''
          mkdir -p "$HOME/.cache/trivy"
          docker save --output "$WORKSPACE/$IMAGE_TAR" "$IMAGE"
          docker run --rm \
            -v "$WORKSPACE":/work \
            -v "$HOME/.cache/trivy":/root/.cache/ \
            aquasec/trivy:latest image \
            --input "/work/$IMAGE_TAR" \
            --severity HIGH,CRITICAL \
            --exit-code 1 \
            --ignore-unfixed \
            --no-progress
        '''
      }
    }

    stage('7. Deploy to Minikube') {
      steps {
        sh '''
          # Make sure kubectl talks to the right cluster
          kubectl config use-context "$MINIKUBE_PROFILE"

          # Load the image into the correct Minikube profile
          docker save "$IMAGE" -o "$WORKSPACE/deploy-img.tar"
          minikube -p "$MINIKUBE_PROFILE" image load "$WORKSPACE/deploy-img.tar"
          rm -f "$WORKSPACE/deploy-img.tar"

          # Stop immediately (with a clear error) if the image did not arrive
          minikube -p "$MINIKUBE_PROFILE" image ls | grep "patient-api:${BUILD_NUMBER}"

          # Deploy
          sed "s/IMAGE_TAG/${BUILD_NUMBER}/" k8s/deployment.yaml | kubectl apply -f -

          # Wait for the rollout; print diagnostics if it fails
          kubectl -n healthcare rollout status deployment/patient-api --timeout=120s || {
            kubectl -n healthcare get pods
            kubectl -n healthcare describe pods -l app=patient-api | tail -40
            exit 1
          }
        '''
      }
    }

    stage('8. DAST (OWASP ZAP)') {
      steps {
        sh '''
          docker network create "$DAST_NET"
          docker run -d --rm --name "$DAST_APP" --network "$DAST_NET" "$IMAGE"
          sleep 8

          chmod -R a+w "$WORKSPACE" || true

          docker run --rm --network "$DAST_NET" \
            -v "$WORKSPACE":/zap/wrk:rw \
            ghcr.io/zaproxy/zaproxy:stable \
            zap-baseline.py -t "http://$DAST_APP:8080" -r zap-report.html -I
        '''
      }
    }
  }

  post {
    always {
      sh '''
        docker stop "$DAST_APP" || true
        docker network rm "$DAST_NET" || true
        rm -f "$WORKSPACE/$IMAGE_TAR"
      '''
      archiveArtifacts artifacts: 'zap-report.html', allowEmptyArchive: true
    }
  }
}