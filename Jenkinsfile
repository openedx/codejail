pipeline {

    agent { label "codejail-worker" }

    options {
        timeout(30)
    }
    stages {
        stage('Install tox') {
            steps {
                withPythonEnv('PYTHON_3.5') {
                    sh '''
                    pip install -r requirements/tox.txt
                    '''
                }
            }
        }

        // Conditional stage: only run in quality checking context.
        stage('Run code quality checks') {
            when {
                environment name: 'TOX_ENV', value: 'quality'
            }
            environment {
                CODEJAIL_TEST_USER = 'sandbox'
                CODEJAIL_TEST_VENV = "/home/sandbox/codejail_sandbox-python${PYTHON_VERSION}"
            }
            steps {
                withPythonEnv('PYTHON_3.5') {
                    script {
                        sh '''
                        tox -e $TOX_ENV
                        '''
                    }
                }
            }
        }

        // Conditional stage: only run for unit testing context (i.e. NOT quality checking).
        stage('Run the tests for each sandbox') {
            when {
                not {
                    environment name: 'TOX_ENV', value: 'quality'
                }
            }
            parallel {
                stage('Run unit tests without proxy') {
                    environment {
                        CODEJAIL_TEST_USER = 'sandbox'
                        CODEJAIL_TEST_VENV = "/home/sandbox/codejail_sandbox-python${PYTHON_VERSION}"
                    }
                    steps {
                        withPythonEnv('PYTHON_3.5') {
                            script {
                                try {
                                    sh '''
                                    tox -e $TOX_ENV
                                    '''
                                } finally {
                                    junit testResults: '**/reports/pytest*.xml'
                                }
                            }
                        }
                     }
                }
            }
        }
    }

    post {
        always {
            deleteDir()
        }
    }

}
