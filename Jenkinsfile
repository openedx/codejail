pipeline {

    agent { label "codejail-worker" }

    options {
        timeout(30)
    }
    stages {
        stage('Install tox') {
            steps {
                withPythonEnv('System-CPython-2.7') {
                    sh '''
                    pip install -r requirements/tox.txt
                    '''
                }
            }
        }

        stage('Run the tests for each sandbox') {
            parallel {
                stage('Run unit tests without proxy') {
                    environment {
                        CODEJAIL_TEST_USER = 'sandbox'
                        CODEJAIL_TEST_VENV = "/home/sandbox/codejail_sandbox-python${PYTHON_VERSION}"
                    }
                    steps {
                        withPythonEnv('System-CPython-2.7') {
                            script {
                                try {
                                    sh '''
                                    tox -e $TOX_ENV
                                    '''
                                } finally {
                                    junit testResults: '**/reports/nosetests*.xml'
                                }
                            }
                        }
                     }
                }
                stage('Run Python3 unit tests without proxy') {
                    environment {
                        CODEJAIL_TEST_USER = 'sandbox'
                        CODEJAIL_TEST_VENV = "/home/sandbox/codejail_sandbox-python2.7"
                    }
                    steps {
                        withPythonEnv('System-CPython-2.7') {
                            script {
                                try {
                                    sh '''
                                    tox -e $TOX_ENV
                                    '''
                                } finally {
                                    junit testResults: '**/reports/nosetests*.xml'
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
