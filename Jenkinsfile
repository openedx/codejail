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
            parallel{
                stage('Run tests with python 2.7') {
                    environment {
                        CODEJAIL_TEST_USER = 'sandbox'
                        CODEJAIL_TEST_VENV = '/home/sandbox/codejail_sandbox-python2-7'
                    }
                    steps {
                        withPythonEnv('System-CPython-2.7') {
                            script {
                                try {
                                    sh '''
                                    sudo -u sandbox /home/sandbox/codejail_sandbox-python2-7/bin/python
                                    tox -e py27
                                    '''
                                } finally {
                                    junit '**/reports/nosetests*.xml'
                                }
                            }
                        }
                     }
                }
                stage('Run tests with python 3.5') {
                    environment {
                        CODEJAIL_TEST_USER = 'sandbox'
                        CODEJAIL_TEST_VENV = '/home/sandbox/codejail_sandbox-python-3-5'
                    }
                    steps {
                        withPythonEnv('System-CPython-2.7') {
                            script {
                                try {
                                    sh '''
                                    tox -e py35
                                    '''
                                } finally {
                                    junit '**/reports/nosetests*.xml'
                                }
                            }
                        }
                     }
                }
                stage('Run tests with python 3.6') {
                    environment {
                        CODEJAIL_TEST_USER = 'sandbox'
                        CODEJAIL_TEST_VENV = '/home/sandbox/codejail_sandbox-python-3-6'
                    }
                    steps {
                        withPythonEnv('System-CPython-2.7') {
                            script {
                                try {
                                    sh '''
                                    tox -e py36
                                    '''
                                } finally {
                                    junit '**/reports/nosetests*.xml'
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
