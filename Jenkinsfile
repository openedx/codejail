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
                                    sudo -u sandbox /home/sandbox/codejail_sandbox-python2-7/bin/python --version
                                    echo "blah";
                                    pip install -r dev-requirements.txt;
                                    make test_no_proxy
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
