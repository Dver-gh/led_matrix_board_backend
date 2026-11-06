pipeline {
    agent any

    environment {
        IMAGE_NAME = "led-backend"
        REGISTRY_URL = "localhost:5000"
        IMAGE_TAG = "${env.BUILD_NUMBER}"
    }

    stages {
        stage('Checkout Code') {
            steps {
                checkout scm
            }
        }
        stage('Security Scan (Gitleaks)') {
            steps {
                sh """
                    docker run --rm \
                      -v ${WORKSPACE}:/path:z \
                      zricethezav/gitleaks:latest \
                      detect --source="/path" --verbose
                """
            }
        }

        stage('Test & Lint via Docker') {
            steps {
                sh "docker build --target test -t ${env.IMAGE_NAME}:test ."
            }
        }

        stage('Build Production Image') {
            steps {
                sh "docker build --target prod -t ${env.IMAGE_NAME}:prod ."
            }
        }

        stage('Publish to Local Registry') {
            steps {
                script {
                    sh "docker tag ${env.IMAGE_NAME}:prod ${env.REGISTRY_URL}/${env.IMAGE_NAME}:${env.IMAGE_TAG}"
		    sh "docker push ${env.REGISTRY_URL}/${env.IMAGE_NAME}:${env.IMAGE_TAG}"                    

		    sh "docker tag ${env.IMAGE_NAME}:prod ${env.REGISTRY_URL}/${env.IMAGE_NAME}:latest"
                    sh "docker push ${env.REGISTRY_URL}/${env.IMAGE_NAME}:latest"
                }
            }
        }
    }

    post {
        always {
            sh "docker image prune -f || true"
        }
        success {
            echo "Pipeline completed successfully! Image pushed to local registry at ${env.REGISTRY_URL}/${env.IMAGE_NAME}:${env.IMAGE_TAG}."
        }
        failure {
            echo "Pipeline failed. Please check the logs above for details."
        }
    }
}
