"""Unit tests for repository analyzer."""
import unittest
from pathlib import Path
from utils.ast_parser import parse_python_file


class TestASTParser(unittest.TestCase):
    """Test AST parser functionality."""
    
    def test_parse_simple_function(self):
        """Test parsing a simple Python function."""
        # Create a temporary test file
        test_code = '''
def hello_world(name: str) -> str:
    """Greet someone."""
    return f"Hello, {name}!"
'''
        test_file = Path(__file__).parent.parent / "test_temp.py"
        test_file.write_text(test_code)
        
        try:
            result = parse_python_file(str(test_file))
            
            self.assertIn('functions', result)
            self.assertEqual(len(result['functions']), 1)
            self.assertEqual(result['functions'][0]['name'], 'hello_world')
        finally:
            # Clean up
            if test_file.exists():
                test_file.unlink()
    
    def test_parse_class(self):
        """Test parsing a Python class."""
        test_code = '''
class TestClass:
    """A test class."""
    
    def method(self, arg: int) -> None:
        """A method."""
        pass
'''
        test_file = Path(__file__).parent.parent / "test_temp.py"
        test_file.write_text(test_code)
        
        try:
            result = parse_python_file(str(test_file))
            
            self.assertIn('classes', result)
            self.assertEqual(len(result['classes']), 1)
            self.assertEqual(result['classes'][0]['name'], 'TestClass')
        finally:
            if test_file.exists():
                test_file.unlink()


if __name__ == '__main__':
    unittest.main()

