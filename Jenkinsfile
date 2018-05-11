pipeline {
  agent {
    node {
      label 'windows'
    }

  }
  stages {
    stage('build') {
      steps {
        withPythonEnv(pythonInstallation: 'Windows-CPython-36') {
          pybat(script: 'pip install .', returnStdout: true)
          pybat 'jenkins.bat'
          git 'https://github.com/common-workflow-language/common-workflow-language.git'
        }

      }
    }
  }
  post {
    always {
      junit 'tests.xml'

    }

  }
}