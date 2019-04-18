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
                stage('Run tests with python 2.7 without proxy') {
                    environment {
                        CODEJAIL_TEST_USER = 'sandbox'
                        CODEJAIL_TEST_VENV = '/home/sandbox/codejail_sandbox-python2.7'
                    }
                    steps {
                        withPythonEnv('System-CPython-2.7') {
                            script {
                                try {
                                    sh '''
                                    tox -e py27
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
