import unittest
from codejail import jail_code
from codejail.safe_exec import SafeExecException, safe_exec


class VagrantCodeJailTest(unittest.TestCase):
    """Very simple test for the codejail in Vagrant."""

    def setUp(self):
        jail_code.configure(
            command='python',
            bin_path='/home/vagrant/sandboxenv/bin/python',
            user='sandbox',
        )

    def run_basic_python_test(self):
        try:
            safe_exec("import os", {}, slug='basic_test')
        except SafeExecException:
            self.fail("`import os` have raised an unwanted SafeExecException!")

    @unittest.skip
    def basic_java_call_test(self):
        def run_unauthorized():
            """
            Runs an unauthorized java command.
            """
            jail_code.jail_code("java", slug='access_denied_java')

        self.assertRaises(SafeExecException, run_unauthorized)

    def process_restriction_test(self):
        def run_unauthorized():
            """
            Runs an unauthorized code that should fail an exception.
            """
            safe_exec(
                "import os\nos.system('ls /etc')",
                {},
                slug='access_denied_python',
            )

        self.assertRaises(Exception, run_unauthorized)
