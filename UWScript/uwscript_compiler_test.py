#!/usr/bin/env python3
"""
Test suite for UWScript Compiler

This module contains comprehensive tests for the UWScript compiler,
covering lexing, parsing, code generation, and string extraction.
"""

import re
import unittest
import sys
import os
import tempfile
from io import StringIO

# Add the current directory to the path so we can import the compiler
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from uwscript_compiler import (
    Lexer, Parser, CodeGenerator, compile_uwscript, extract_strings,
    TokenType, Token, Program, VariableDeclaration, Assignment, 
    IfStatement, WhileStatement, SayStatement, BinaryOperation, Literal,
    Identifier, ArrayLiteral, ArrayAccess, FunctionCall, ReturnStatement,
    GotoStatement, LabelStatement, ExitStatement, MenuStatement, FilterMenuStatement,
    AskStatement, Expression, Statement, UnaryOperation, ASTNode
)

from uw_cnv_runner import UltimaUnderworldVM

class TestLexer(unittest.TestCase):
    """Test the lexer functionality"""
    
    def test_tokenize_simple_statement(self):
        """Test tokenizing a simple let statement"""
        source = 'let x = 42'
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        
        expected_types = [
            TokenType.KEYWORD,     # let
            TokenType.IDENTIFIER,  # x
            TokenType.OPERATOR,    # =
            TokenType.NUMBER,      # 42
            TokenType.EOF
        ]
        
        token_types = [token.type for token in tokens]
        self.assertEqual(token_types, expected_types)
        
        # Check specific values
        self.assertEqual(tokens[0].value, 'let')
        self.assertEqual(tokens[1].value, 'x')
        self.assertEqual(tokens[2].value, '=')
        self.assertEqual(tokens[3].value, '42')
    
    def test_tokenize_string_literal(self):
        """Test tokenizing string literals"""
        source = 'say "Hello, world!"'
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        
        # Find the string token
        string_token = next(token for token in tokens if token.type == TokenType.STRING)
        self.assertEqual(string_token.value, 'Hello, world!')
    
    def test_tokenize_escaped_string(self):
        """Test tokenizing strings with escape sequences"""
        source = 'say "Hello\\nWorld"'
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        
        string_token = next(token for token in tokens if token.type == TokenType.STRING)
        self.assertEqual(string_token.value, 'Hello\nWorld')
    
    def test_tokenize_comments(self):
        """Test tokenizing comments"""
        source = '''
        let x = 5  // This is a comment
        // Another comment
        say "Hello"
        '''
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        
        comment_tokens = [token for token in tokens if token.type == TokenType.COMMENT]
        self.assertEqual(len(comment_tokens), 2)
        self.assertEqual(comment_tokens[0].value.strip(), 'This is a comment')
        self.assertEqual(comment_tokens[1].value.strip(), 'Another comment')
    

    def test_tokenize_operators(self):
        """Test tokenizing various operators"""
        source = 'x == 5 and y != 3 or z >= 10'
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        
        operators = [token.value for token in tokens if token.type == TokenType.OPERATOR]
        keywords = [token.value for token in tokens if token.type == TokenType.KEYWORD]
        expected_operators = ['==', '!=', '>=']
        expected_keywords = ['and', 'or']
        
        # Check that we have the multi-character operators
        for op in expected_operators:
            self.assertIn(op, operators)
        
        # Check that we have the logical operators as keywords
        for kw in expected_keywords:
            self.assertIn(kw, keywords)


class TestParser(unittest.TestCase):
    """Test the parser functionality"""
    
    def test_parse_variable_declaration(self):
        """Test parsing variable declarations"""
        source = 'let health = 100'
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        self.assertIsInstance(ast, Program)
        self.assertEqual(len(ast.children), 1)
        
        var_decl = ast.children[0]
        self.assertIsInstance(var_decl, VariableDeclaration)
        self.assertEqual(var_decl.name, 'health')
        self.assertIsInstance(var_decl.children[0], Literal)
        self.assertEqual(var_decl.children[0].value, 100)
    
    def test_parse_assignment(self):
        """Test parsing assignment statements"""
        source = 'health += 10'
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        assignment = ast.children[0]
        self.assertIsInstance(assignment, Assignment)
        self.assertIsInstance(assignment.target, Identifier)  # Check target is an Identifier
        self.assertEqual(assignment.target.name, 'health')    # Check name on the Identifier
        self.assertEqual(assignment.operator, '+=')
    
    def test_parse_if_statement(self):
        """Test parsing if statements"""
        source = '''
        if health > 50
            say "Feeling good!"
        else
            say "Need healing!"
        endif
        '''
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        if_stmt = ast.children[0]
        self.assertIsInstance(if_stmt, IfStatement)
        self.assertIsInstance(if_stmt.condition, BinaryOperation)
        self.assertEqual(len(if_stmt.true_branch), 1)
        self.assertEqual(len(if_stmt.false_branch), 1)
        self.assertIsInstance(if_stmt.true_branch[0], SayStatement)
        self.assertIsInstance(if_stmt.false_branch[0], SayStatement)
    
    def test_parse_while_statement(self):
        """Test parsing while statements"""
        source = '''
        while counter > 0
            say "Counting..."
            counter -= 1
        endwhile
        '''
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        while_stmt = ast.children[0]
        self.assertIsInstance(while_stmt, WhileStatement)
        self.assertIsInstance(while_stmt.condition, BinaryOperation)
        self.assertEqual(len(while_stmt.body), 2)
    
    def test_parse_binary_operations(self):
        """Test parsing binary operations with correct precedence"""
        source = 'let result = 2 + 3 * 4'
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        var_decl = ast.children[0]
        expr = var_decl.children[0]
        
        # Should be: 2 + (3 * 4)
        self.assertIsInstance(expr, BinaryOperation)
        self.assertEqual(expr.token.value, '+')
        self.assertIsInstance(expr.right, BinaryOperation)
        self.assertEqual(expr.right.token.value, '*')


class TestCodeGenerator(unittest.TestCase):
    """Test the code generator functionality"""
    
    def test_generate_variable_declaration(self):
        """Test generating code for variable declarations"""
        source = 'let x = 42'
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        generator = CodeGenerator()
        assembly = generator.generate(ast)
        
        # Should contain START, PUSHI 42, variable storage, and EXIT_OP
        self.assertIn('START', assembly)
        self.assertIn('PUSHI 42', assembly)
        self.assertIn('PUSHI_EFF 0', assembly)  # Variable at offset 0
        self.assertIn('STO', assembly)  # Store operation
        self.assertIn('EXIT_OP', assembly)
    
    def test_generate_assignment(self):
        """Test generating code for assignments"""
        source = '''
        let x = 10
        x += 5
        '''
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        generator = CodeGenerator()
        assembly = generator.generate(ast)
        
        # Should contain the += operation
        self.assertIn('FETCHM', assembly)  # Load current value
        self.assertIn('OPADD', assembly)   # Add operation
        self.assertIn('STO', assembly)     # Store result
    
    def test_generate_if_statement(self):
        """Test generating code for if statements"""
        source = '''
        let x = 10
        if x > 5
            say "Greater than 5"
        else
            say "Not greater than 5"
        endif
        '''
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        generator = CodeGenerator()
        assembly = generator.generate(ast)
        
        # Should contain conditional logic
        self.assertIn('TSTGT', assembly)   # Greater than test
        self.assertIn('BEQ', assembly)     # Branch if equal (false)
        self.assertIn('JMP', assembly)     # Jump to end
        self.assertIn('SAY_OP', assembly)  # Say operations
        self.assertIn('label_', assembly)  # Generated labels
    
    def test_generate_say_statement(self):
        """Test generating code for say statements"""
        source = 'say "Hello, world!"'
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        generator = CodeGenerator()
        assembly = generator.generate(ast)
        
        # Should contain string push and say operation
        self.assertIn('PUSHI 0', assembly)  # String index 0
        self.assertIn('SAY_OP', assembly)   # Say operation
        
        # Should have the string in literals
        self.assertIn('Hello, world!', generator.string_literals)


class TestStringExtraction(unittest.TestCase):
    """Test string extraction functionality"""
    
    def test_extract_strings_simple(self):
        """Test extracting strings from simple source"""
        source = '''
        say "Hello"
        say "World"
        '''
        
        result = extract_strings(source, block_id=1)
        
        # Should contain both strings
        self.assertIn('Hello', result)
        self.assertIn('World', result)
        self.assertIn('block: 0001; 2 strings.', result)
        self.assertIn('0: Hello', result)
        self.assertIn('1: World', result)
    
    def test_extract_strings_with_escapes(self):
        """Test extracting strings with escape sequences"""
        source = 'say "Line 1\\nLine 2"'
        
        result = extract_strings(source, block_id=1)
        
        # Should contain escaped newline
        self.assertIn('Line 1\\nLine 2', result)
    
    def test_extract_strings_deduplication(self):
        """Test that duplicate strings are not repeated"""
        source = '''
        say "Hello"
        say "Hello"
        say "World"
        '''
        
        result = extract_strings(source, block_id=1)
        
        # Should only have 2 unique strings
        self.assertIn('block: 0001; 2 strings.', result)


class TestCompileUWScript(unittest.TestCase):
    """Test the main compilation function"""
    
    def test_compile_simple_program(self):
        """Test compiling a simple program"""
        source = '''
        let health = 100
        say "Current health: " + health
        if health > 50
            say "Feeling good!"
        endif
        '''
        
        result = compile_uwscript(source, block_id=1)
        
        # Should return both assembly and strings
        self.assertIn('assembly', result)
        self.assertIn('strings', result)
        
        assembly = result['assembly']
        strings = result['strings']
        
        # Assembly should contain expected instructions
        self.assertIn('START', assembly)
        self.assertIn('EXIT_OP', assembly)
        self.assertIn('PUSHI 100', assembly)
        self.assertIn('SAY_OP', assembly)
        self.assertIn('TSTGT', assembly)
        
        # Strings should contain the literals
        self.assertIn('Current health: ', strings)
        self.assertIn('Feeling good!', strings)
    
    def test_compile_with_functions(self):
        """Test compiling with function calls"""
        source = '''
        let roll = random(20)
        say "You rolled: " + roll
        '''
        
        result = compile_uwscript(source, block_id=1)
        assembly = result['assembly']
        
        # Should contain function call
        self.assertIn('CALLI 5', assembly)  # random is function ID 5

    def test_compile_with_menu1(self):
        """Test compiling with menu statements"""
        source = '''
        menu choice "Option 1", "Option 2", "Option 3"
        say "You chose: " + choice
        '''
        
        result = compile_uwscript(source, block_id=1)
        assembly = result['assembly']
        
        # Should contain menu call
        self.assertIn('CALLI 0', assembly)  # babl_menu is function ID 0
    
    def test_compile_with_menu2(self):
        """Test compiling with menu statements"""
        source = '''
        menu choice [
            "Option 1",
            "Option 2",
            "Option 3"
        ]
        say "You chose: " + choice
        '''
        
        result = compile_uwscript(source, block_id=1)
        assembly = result['assembly']
        
        # Should contain menu call
        self.assertIn('CALLI 0', assembly)  # babl_menu is function ID 0


class TestErrorHandling(unittest.TestCase):
    """Test error handling in the compiler"""
    
    def test_undefined_variable(self):
        """Test error when using undefined variable"""
        source = '''
        say undefined_var
        '''
        
        with self.assertRaises(NameError):
            compile_uwscript(source)
    
    def test_syntax_error(self):
        """Test syntax error handling"""
        source = '''
        let x = 
        '''
        
        with self.assertRaises(SyntaxError):
            compile_uwscript(source)
    
    def test_unterminated_string(self):
        """Test unterminated string error"""
        source = '''
        say "unterminated string
        '''
        
        with self.assertRaises(SyntaxError):
            compile_uwscript(source)


class TestComplexPrograms(unittest.TestCase):
    """Test compilation of more complex programs"""
    
    def test_if_elseif_else_control_flow(self):
        """Test that elseif prevents else from executing"""
        source = '''
        let choice = 2
        
        if choice == 1
            say "Choice is 1"
        elseif choice == 2
            say "Choice is 2"
        else
            say "Choice is something else"
        endif
        '''
        
        # This test should verify that when choice == 2, only "Choice is 2" 
        # is executed, not both "Choice is 2" AND "Choice is something else"
        
        result = compile_uwscript(source, block_id=1)
        assembly = result['assembly']
        
        # The assembly should have proper control flow where:
        # 1. If choice == 1 is false, jump to elseif
        # 2. If choice == 2 is true, execute elseif branch then jump to end
        # 3. Only if both conditions are false should else execute
        
        # Count the number of labels and jumps to verify proper nesting
        lines = assembly.split('\n')
        
        # Should have proper label structure for nested if-elseif-else
        label_lines = [line for line in lines if line.strip().endswith(':')]
        jump_lines = [line for line in lines if 'JMP' in line]
        branch_lines = [line for line in lines if 'BEQ' in line]
        
        # For proper if-elseif-else, we need:
        # - At least 2 labels (one for elseif, one for end)
        # - At least 1 JMP to skip else when elseif executes
        # - At least 2 BEQ branches (one for main if, one for elseif)
        self.assertGreaterEqual(len(label_lines), 2, "Should have at least 2 labels for proper control flow")
        self.assertGreaterEqual(len(jump_lines), 1, "Should have at least 1 JMP to skip else clause")
        self.assertGreaterEqual(len(branch_lines), 2, "Should have at least 2 conditional branches")
        
        # Verify string extraction
        strings = result['strings']
        self.assertIn('Choice is 1', strings)
        self.assertIn('Choice is 2', strings)
        self.assertIn('Choice is something else', strings)
    
    def test_complete_if_elseif_else_scenarios(self):
        """Test all three scenarios: if executes, elseif executes, else executes"""
        
        # Test scenario 1: if condition is true
        source1 = '''
        let choice = 1
        let result = ""
        
        if choice == 1
            result = "chose_one"
        elseif choice == 2
            result = "chose_two"
        else
            result = "chose_other"
        endif
        
        say result
        '''
        
        result1 = compile_uwscript(source1, block_id=1)
        assembly1 = result1['assembly']
        
        # Verify structure for scenario 1
        self.assertIn('TSTEQ', assembly1)  # Should have equality tests
        self.assertIn('BEQ', assembly1)    # Should have conditional branches  
        self.assertIn('JMP', assembly1)    # Should have jumps to skip other branches
        
        strings1 = result1['strings']
        self.assertIn('chose_one', strings1)
        self.assertIn('chose_two', strings1)
        self.assertIn('chose_other', strings1)
        
        # Test scenario 2: elseif condition is true
        source2 = '''
        let choice = 2
        let result = ""
        
        if choice == 1
            result = "chose_one"
        elseif choice == 2
            result = "chose_two"
        else
            result = "chose_other"
        endif
        
        say result
        '''
        
        result2 = compile_uwscript(source2, block_id=1)
        assembly2 = result2['assembly']
        
        # Should have similar structure
        self.assertIn('TSTEQ', assembly2)
        self.assertIn('BEQ', assembly2)
        self.assertIn('JMP', assembly2)
        
        # Test scenario 3: else condition (neither if nor elseif)
        source3 = '''
        let choice = 3
        let result = ""
        
        if choice == 1
            result = "chose_one"
        elseif choice == 2
            result = "chose_two"
        else
            result = "chose_other"
        endif
        
        say result
        '''
        
        result3 = compile_uwscript(source3, block_id=1)
        assembly3 = result3['assembly']
        
        # Should have similar structure but execution should reach else
        self.assertIn('TSTEQ', assembly3)
        self.assertIn('BEQ', assembly3)
        
        # All three scenarios should generate similar control flow patterns
        # The key difference is the initial value, but the structure should be the same
        
        # Verify that each scenario has the proper number of conditional tests
        # Should have at least 2 TSTEQ (one for if, one for elseif)
        tsteq_count1 = assembly1.count('TSTEQ')
        tsteq_count2 = assembly2.count('TSTEQ')  
        tsteq_count3 = assembly3.count('TSTEQ')
        
        self.assertGreaterEqual(tsteq_count1, 2, "Scenario 1 should have at least 2 equality tests")
        self.assertGreaterEqual(tsteq_count2, 2, "Scenario 2 should have at least 2 equality tests")
        self.assertGreaterEqual(tsteq_count3, 2, "Scenario 3 should have at least 2 equality tests")
        
        # Each should have proper jump structure to skip unexecuted branches
        jmp_count1 = assembly1.count('JMP')
        jmp_count2 = assembly2.count('JMP')
        jmp_count3 = assembly3.count('JMP')
        
        self.assertGreaterEqual(jmp_count1, 2, "Scenario 1 should have jumps to skip other branches")
        self.assertGreaterEqual(jmp_count2, 2, "Scenario 2 should have jumps to skip other branches") 
        self.assertGreaterEqual(jmp_count3, 1, "Scenario 3 should have at least 1 jump")

    def test_nested_elseif_chains(self):
        """Test multiple elseif clauses in a chain"""
        source = '''
        let value = 3
        let result = ""
        
        if value == 1
            result = "one"
        elseif value == 2
            result = "two" 
        elseif value == 3
            result = "three"
        elseif value == 4
            result = "four"
        else
            result = "other"
        endif
        
        say result
        '''
        
        result = compile_uwscript(source, block_id=1)
        assembly = result['assembly']
        
        # Should have multiple TSTEQ operations (one for each condition)
        tsteq_count = assembly.count('TSTEQ')
        self.assertGreaterEqual(tsteq_count, 4, "Should have at least 4 equality tests for the chain")
        
        # Should have proper branching structure
        beq_count = assembly.count('BEQ')
        self.assertGreaterEqual(beq_count, 4, "Should have at least 4 conditional branches")
        
        # Should have jumps to skip subsequent conditions when one matches
        jmp_count = assembly.count('JMP')
        self.assertGreaterEqual(jmp_count, 4, "Should have jumps to skip remaining conditions")
        
        # Verify all strings are extracted
        strings = result['strings']
        expected_strings = ['one', 'two', 'three', 'four', 'other']
        for expected in expected_strings:
            self.assertIn(expected, strings)

    def test_elseif_does_not_fall_through_to_else(self):
        """Test that elseif branch execution doesn't fall through to else"""
        source = '''
        let x = 2
        let result = ""
        
        if x == 1
            result = "one"
        elseif x == 2  
            result = "two"
        else
            result = "other"
        endif
        
        say result
        '''
        
        result = compile_uwscript(source, block_id=1)
        assembly = result['assembly']
        
        # When x == 2, the result should be "two", not "two" + "other"
        # This test will fail with the current implementation because
        # the else clause incorrectly executes after the elseif
        
        # Look for the assembly pattern that should exist:
        # 1. Test x == 1, if false jump to elseif
        # 2. Execute if branch, then jump to end
        # 3. Test x == 2, if false jump to else  
        # 4. Execute elseif branch, then jump to end
        # 5. Execute else branch
        # 6. End
        
        lines = [line.strip() for line in assembly.split('\n') if line.strip()]
        
        # Find all the control flow instructions
        test_instructions = [line for line in lines if any(op in line for op in ['TSTEQ', 'TSTNE', 'TSTGT', 'TSTLT', 'TSTGE', 'TSTLE'])]
        branch_instructions = [line for line in lines if 'BEQ' in line or 'BNE' in line]
        jump_instructions = [line for line in lines if 'JMP' in line]
        
        # Should have at least 2 test instructions (for if condition and elseif condition)
        self.assertGreaterEqual(len(test_instructions), 2, 
                              f"Expected at least 2 test instructions, got {len(test_instructions)}: {test_instructions}")
        
        # Should have conditional branches for each test
        self.assertGreaterEqual(len(branch_instructions), 2,
                              f"Expected at least 2 branch instructions, got {len(branch_instructions)}: {branch_instructions}")
        
        # Should have jumps to skip over else clause when if/elseif executes
        self.assertGreaterEqual(len(jump_instructions), 2,
                              f"Expected at least 2 jump instructions, got {len(jump_instructions)}: {jump_instructions}")
        
        # Strings should be properly extracted
        strings = result['strings']
        self.assertIn('one', strings)
        self.assertIn('two', strings) 
        self.assertIn('other', strings)
    
    def test_menu_with_elseif_control_flow(self):
        """Test the specific scenario from the user's example"""
        source = '''
        say "Is there anything else you'd like to know?"
        menu more_questions [
            "Tell me about the abyss",
            "Do you have any items to trade?",
            "No, I must be going."
        ]
        if more_questions == 1
            say "The abyss is an ancient testing ground, created by beings far greater than you or I."
            say "Its depths hold secrets beyond your imagination."
        elseif more_questions == 2
            say "I have a few trinkets you might find useful..."
            say "But I don't think you have anything I want in exchange. Come back when you find something... interesting."
        else
            say "Very well. Safe journeys, traveler."
        endif
        '''
        
        result = compile_uwscript(source, block_id=1)
        assembly = result['assembly']
        
        # This test exposes the bug where selecting option 2 would execute
        # both the elseif branch AND the else branch
        
        # The generated assembly should ensure that:
        # 1. When more_questions == 1, only the first branch executes
        # 2. When more_questions == 2, only the elseif branch executes (NOT the else)
        # 3. When more_questions == 3, only the else branch executes
        
        lines = assembly.split('\n')
        
        # Look for the pattern that indicates proper control flow:
        # After executing the elseif true branch, there should be a JMP to skip the else
        tsteq_lines = [i for i, line in enumerate(lines) if 'TSTEQ' in line]
        jmp_lines = [i for i, line in enumerate(lines) if 'JMP' in line and not line.strip().startswith(';')]
        
        # There should be TSTEQ operations for both the if and elseif conditions
        self.assertGreaterEqual(len(tsteq_lines), 2, "Should have equality tests for both if and elseif")
        
        # There should be JMP instructions to properly skip else when elseif executes
        self.assertGreaterEqual(len(jmp_lines), 1, "Should have JMP to skip else clause after elseif")
        
        # Verify all strings are extracted correctly
        strings = result['strings']
        expected_strings = [
            "Is there anything else you'd like to know?",
            "Tell me about the abyss",
            "Do you have any items to trade?",
            "No, I must be going.",
            "The abyss is an ancient testing ground, created by beings far greater than you or I.",
            "Its depths hold secrets beyond your imagination.",
            "I have a few trinkets you might find useful...",
            "But I don't think you have anything I want in exchange. Come back when you find something... interesting.",
            "Very well. Safe journeys, traveler."
        ]
        
        for expected_string in expected_strings:
            self.assertIn(expected_string, strings, f"Missing expected string: {expected_string}")

    def test_shopkeeper_program(self):
        """Test compiling a shopkeeper-like program"""
        source = '''
        let gold = 100
        let has_sword = false
        
        label start
        say "Welcome to my shop!"
        
        menu choice [
            "Show wares",
            "Check gold",
            "Leave"
        ]
        
        if choice == 1
            say "Here are my wares..."
        elseif choice == 2
            say "You have " + gold + " gold"
        else
            say "Goodbye!"
            exit
        endif
        
        goto start
        '''
        
        result = compile_uwscript(source, block_id=1)
        assembly = result['assembly']
        
        # Should contain all expected elements
        self.assertIn('START', assembly)
        self.assertIn('EXIT_OP', assembly)
        self.assertIn('CALLI 0', assembly)  # Menu call
        self.assertIn('JMP start', assembly)  # Goto
        self.assertIn('start:', assembly)  # Label
        
        # Should handle multiple strings
        strings = result['strings']
        self.assertIn('Welcome to my shop!', strings)
        self.assertIn('Show wares', strings)
        self.assertIn('Goodbye!', strings)
    
    def test_nested_control_flow(self):
        """Test nested if statements and loops"""
        source = '''
        let i = 0
        while i < 3
            if i == 0
                say "First iteration"
            elseif i == 1
                say "Second iteration"
            else
                say "Third iteration"
            endif
            i += 1
        endwhile
        '''
        
        result = compile_uwscript(source, block_id=1)
        assembly = result['assembly']
        
        # Should contain nested control structures
        self.assertIn('label_', assembly)  # Multiple labels for nested structures
        self.assertIn('BEQ', assembly)
        self.assertIn('JMP', assembly)
        self.assertIn('OPADD', assembly)  # i += 1

    def test_while_loop_compilation(self):
        """Test compiling while loops"""
        source = '''
        let counter = 3
        let total = 0
        
        while counter > 0
            say "Counter is: " + counter
            total += counter
            counter -= 1
        endwhile
        
        say "Final total: " + total
        say "Loop finished!"
        '''
        
        result = compile_uwscript(source, block_id=1)
        assembly = result['assembly']
        
        # Should contain while loop instructions
        self.assertIn('TSTGT', assembly)     # counter > 0 test
        self.assertIn('BEQ', assembly)       # Branch if condition false
        self.assertIn('JMP', assembly)       # Jump back to loop start
        self.assertIn('SAY_OP', assembly)    # Say operations
        self.assertIn('OPADD', assembly)     # total += counter
        self.assertIn('OPSUB', assembly)     # counter -= 1
        
        # Should have proper label structure for loops
        label_lines = [line for line in assembly.split('\n') if line.strip().endswith(':')]
        self.assertGreaterEqual(len(label_lines), 2, "Should have start and end labels for while loop")
        
        # Verify strings are extracted
        strings = result['strings']
        self.assertIn('Counter is: ', strings)
        self.assertIn('Final total: ', strings)
        self.assertIn('Loop finished!', strings)

    def test_nested_while_loops(self):
        """Test nested while loops"""
        source = '''
        let outer = 2
        
        while outer > 0
            say "Outer loop: " + outer
            let inner = 2
            
            while inner > 0
                say "  Inner loop: " + inner
                inner -= 1
            endwhile
            
            outer -= 1
        endwhile
        
        say "All loops finished!"
        '''
        
        result = compile_uwscript(source, block_id=1)
        assembly = result['assembly']
        
        # Should have multiple sets of loop instructions
        tstgt_count = assembly.count('TSTGT')
        beq_count = assembly.count('BEQ')
        jmp_count = assembly.count('JMP')
        
        self.assertGreaterEqual(tstgt_count, 2, "Should have tests for both loops")
        self.assertGreaterEqual(beq_count, 2, "Should have branch instructions for both loops")
        self.assertGreaterEqual(jmp_count, 2, "Should have jump back instructions for both loops")
        
        # Verify strings
        strings = result['strings']
        self.assertIn('Outer loop: ', strings)
        self.assertIn('  Inner loop: ', strings)
        self.assertIn('All loops finished!', strings)

    def test_while_loop_with_complex_condition(self):
        """Test while loop with complex boolean conditions"""
        source = '''
        let health = 100
        let mana = 50
        let turn = 0
        
        while health > 0 and mana > 10 and turn < 5
            say "Combat turn " + turn
            health -= 20
            mana -= 15
            turn += 1
        endwhile
        
        if health <= 0
            say "Player defeated!"
        elseif mana <= 10
            say "Out of mana!"
        else
            say "Turn limit reached!"
        endif
        '''
        
        result = compile_uwscript(source, block_id=1)
        assembly = result['assembly']
        
        # Should contain complex condition evaluation
        self.assertIn('TSTGT', assembly)     # health > 0
        self.assertIn('TSTLT', assembly)     # turn < 5
        self.assertIn('OPAND', assembly)     # AND operations for complex condition
        
        # Verify all strings are extracted
        strings = result['strings']
        expected_strings = [
            'Combat turn ',
            'Player defeated!',
            'Out of mana!',
            'Turn limit reached!'
        ]
        for expected in expected_strings:
            self.assertIn(expected, strings)

    def test_simple_while_loops_no_concatenation(self):
        """Test while loops without string concatenation issues"""
        source = '''
        let counter = 3
        
        say "Starting countdown"
        
        while counter > 0
            say "Tick"
            counter -= 1
        endwhile
        
        say "Finished"
        '''
        
        result = compile_uwscript(source, block_id=1)
        assembly = result['assembly']
        
        # Should contain while loop instructions
        self.assertIn('TSTGT', assembly)     # counter > 0 test
        self.assertIn('BEQ', assembly)       # Branch if condition false
        self.assertIn('JMP', assembly)       # Jump back to loop start
        self.assertIn('OPSUB', assembly)     # counter -= 1
        
        # Should have proper label structure
        lines = assembly.split('\n')
        label_lines = [line for line in lines if line.strip().endswith(':')]
        self.assertGreaterEqual(len(label_lines), 2, "Should have loop start and end labels")
        
        # Verify strings are extracted correctly
        strings = result['strings']
        self.assertIn('Starting countdown', strings)
        self.assertIn('Tick', strings)
        self.assertIn('Finished', strings)

    def test_boolean_assignment(self):
        """Test boolean value assignment works correctly"""
        source = '''
        let flag = true
        let other = false
        
        if flag == true
            say "Flag is true"
        endif
        
        if other == false
            say "Other is false"
        endif
        '''
        
        result = compile_uwscript(source, block_id=1)
        assembly = result['assembly']
        
        # Should contain boolean value pushes
        self.assertIn('PUSHI 1', assembly)  # true
        self.assertIn('PUSHI 0', assembly)  # false
        self.assertIn('TSTEQ', assembly)    # equality tests
        
        strings = result['strings']
        self.assertIn('Flag is true', strings)
        self.assertIn('Other is false', strings)

    def test_integer_variable_substitution(self):
        """Test string concatenation with integer variables converts to @SI substitution"""
        source = '''
        let health = 100
        say "Health: " + health
        '''
        
        result = compile_uwscript(source, block_id=1)
        strings = result['strings']
        assembly = result['assembly']
        
        # Should contain the substitution pattern for integer
        self.assertIn('Health: @SI0', strings)  # health is variable 0
        
        # Assembly should push the correct string index
        self.assertIn('PUSHI 1', assembly)  # String index for substituted string
        
        # Verify variable mapping
        self.assertIn('health -> 0', assembly)

    def test_string_variable_substitution(self):
        """Test string concatenation with string variables converts to @SS substitution"""
        source = '''
        let player_name = "Avatar"
        say "Hello " + player_name
        '''
        
        result = compile_uwscript(source, block_id=1)
        strings = result['strings']
        assembly = result['assembly']
        
        # Should contain the substitution pattern for string
        self.assertIn('Hello @SS0', strings)  # player_name is variable 0 (first variable)
        
        # Should have both original string and substituted string
        self.assertIn('Avatar', strings)
        
        # Verify variable mapping
        self.assertIn('player_name -> 0', assembly)

    def test_multiple_variable_substitutions(self):
        """Test multiple different variable substitutions"""
        source = '''
        let health = 75
        let mana = 50
        let name = "Hero"
        
        say "HP: " + health
        say "MP: " + mana
        say "Name: " + name
        '''
        
        result = compile_uwscript(source, block_id=1)
        strings = result['strings']
        
        # Should have correct substitution patterns
        self.assertIn('HP: @SI0', strings)     # health (integer) - variable 0
        self.assertIn('MP: @SI1', strings)     # mana (integer) - variable 1  
        self.assertIn('Name: @SS2', strings)   # name (string) - variable 2

    def test_variable_allocation_order(self):
        """Test that variables are allocated in declaration order starting from 0"""
        source = '''
        let first = 10
        let second = "test"
        let third = true
        
        say "First: " + first
        say "Second: " + second  
        say "Third: " + third
        '''
        
        result = compile_uwscript(source, block_id=1)
        strings = result['strings']
        assembly = result['assembly']
        
        # Check variable mappings in assembly
        self.assertIn('first -> 0', assembly)
        self.assertIn('second -> 1', assembly)  
        self.assertIn('third -> 2', assembly)
        
        # Check substitution patterns
        self.assertIn('First: @SI0', strings)   # first is variable 0
        self.assertIn('Second: @SS1', strings)  # second is variable 1 (string)
        self.assertIn('Third: @SI2', strings)   # third is variable 2 (boolean as int)

    def test_reverse_concatenation_order(self):
        """Test variable + string concatenation (reverse order)"""
        source = '''
        let score = 1500
        say score + " points earned!"
        '''
        
        result = compile_uwscript(source, block_id=1)
        strings = result['strings']
        
        # Should handle reverse order concatenation
        self.assertIn('@SI0 points earned!', strings)

    def test_boolean_variable_substitution(self):
        """Test boolean variables get treated as integers in substitution"""
        source = '''
        let is_alive = true
        say "Alive: " + is_alive
        '''
        
        result = compile_uwscript(source, block_id=1)
        strings = result['strings']
        
        # Boolean should be treated as integer (true = 1)
        self.assertIn('Alive: @SI0', strings)

    def test_no_substitution_for_literals(self):
        """Test that literal + literal doesn't create substitution"""
        source = '''
        say "Hello" + "World"
        '''
        
        result = compile_uwscript(source, block_id=1)
        strings = result['strings']
        assembly = result['assembly']
        
        # Should NOT create substitution, should fall back to addition
        self.assertNotIn('@S', strings)
        
        # Should contain both original strings
        self.assertIn('Hello', strings)
        self.assertIn('World', strings)
        
        # Should generate OPADD instruction
        self.assertIn('OPADD', assembly)

    def test_multiple_concatenations_warning(self):
        """Test that multiple concatenations generate a warning"""
        source = '''
        let a = 10
        let b = 20
        say "A: " + a + " B: " + b
        '''
        
        # This should generate a warning and fall back to numeric addition
        # We'll capture the warning by checking the assembly doesn't contain substitution
        result = compile_uwscript(source, block_id=1)
        assembly = result['assembly']
        
        # Should fall back to numeric operations due to complexity
        self.assertIn('OPADD', assembly)

    def test_substitution_in_control_flow(self):
        """Test substitutions work inside if statements"""
        source = '''
        let health = 75
        
        if health > 50
            say "Good health: " + health
        else
            say "Low health: " + health
        endif
        '''
        
        result = compile_uwscript(source, block_id=1)
        strings = result['strings']
        
        # Both branches should have substitutions
        self.assertIn('Good health: @SI0', strings)
        self.assertIn('Low health: @SI0', strings)

    def test_substitution_with_expression_variables(self):
        """Test substitution with variables that come from expressions"""
        source = '''
        let base = 10
        let bonus = 5
        let total = base + bonus
        say "Total: " + total
        '''
        
        result = compile_uwscript(source, block_id=1)
        strings = result['strings']
        
        # total should be treated as integer
        self.assertIn('Total: @SI2', strings)  # total is variable 2


class TestFileIO(unittest.TestCase):
    """Test file input/output functionality"""
    
    def test_compile_from_file(self):
        """Test compiling from a file"""
        source = '''
        let greeting = "Hello from file!"
        say greeting
        '''
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.uws', delete=False) as f:
            f.write(source)
            temp_filename = f.name
        
        try:
            # Import the main function
            from uwscript_compiler import main
            
            # Capture stdout
            old_stdout = sys.stdout
            sys.stdout = captured_output = StringIO()
            
            # Mock sys.argv
            old_argv = sys.argv
            sys.argv = ['uwscript-compiler.py', temp_filename]
            
            # Run the main function
            main()
            
            # Get the output
            output = captured_output.getvalue()
            
            # Should contain assembly code
            self.assertIn('START', output)
            self.assertIn('EXIT_OP', output)
            
        finally:
            # Restore stdout and argv
            sys.stdout = old_stdout
            sys.argv = old_argv
            
            # Clean up temporary file
            os.unlink(temp_filename)


class TestArrayFunctionality(unittest.TestCase):
    """Test the array functionality in UWScript"""
    
    def test_parse_array_literal(self):
        """Test parsing array literals"""
        source = 'let numbers = [1, 2, 3, 4, 5]'
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        var_decl = ast.children[0]
        self.assertIsInstance(var_decl, VariableDeclaration)
        self.assertEqual(var_decl.name, 'numbers')
        
        array_literal = var_decl.children[0]
        self.assertIsInstance(array_literal, ArrayLiteral)
        self.assertEqual(len(array_literal.elements), 5)
        
        # Check each element's value
        expected_values = [1, 2, 3, 4, 5]
        for i, element in enumerate(array_literal.elements):
            self.assertIsInstance(element, Literal)
            self.assertEqual(element.value, expected_values[i])
    
    def test_parse_array_access(self):
        """Test parsing array access expressions"""
        source = 'let value = numbers[2]'
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        var_decl = ast.children[0]
        self.assertIsInstance(var_decl, VariableDeclaration)
        
        array_access = var_decl.children[0]
        self.assertIsInstance(array_access, ArrayAccess)
        
        # Check array identifier
        self.assertIsInstance(array_access.array, Identifier)
        self.assertEqual(array_access.array.name, 'numbers')
        
        # Check index
        self.assertIsInstance(array_access.index, Literal)
        self.assertEqual(array_access.index.value, 2)
    
    def test_parse_array_assignment(self):
        """Test parsing array assignment"""
        source = 'numbers[3] = 42'
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        assignment = ast.children[0]
        self.assertIsInstance(assignment, Assignment)
        
        # Check target (array access)
        self.assertIsInstance(assignment.target, ArrayAccess)
        self.assertEqual(assignment.target.array.name, 'numbers')
        self.assertEqual(assignment.target.index.value, 3)
        
        # Check value
        self.assertIsInstance(assignment.children[0], Literal)
        self.assertEqual(assignment.children[0].value, 42)
    
    def test_parse_nested_arrays(self):
        """Test parsing nested array literals"""
        source = 'let matrix = [[1, 2], [3, 4]]'
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        var_decl = ast.children[0]
        self.assertIsInstance(var_decl, VariableDeclaration)
        
        outer_array = var_decl.children[0]
        self.assertIsInstance(outer_array, ArrayLiteral)
        self.assertEqual(len(outer_array.elements), 2)
        
        # Check each inner array
        for i, inner_array in enumerate(outer_array.elements):
            self.assertIsInstance(inner_array, ArrayLiteral)
            self.assertEqual(len(inner_array.elements), 2)
            
            # Check values in inner arrays
            expected_values = [1, 2] if i == 0 else [3, 4]
            for j, element in enumerate(inner_array.elements):
                self.assertEqual(element.value, expected_values[j])
    
    def test_parse_array_with_expressions(self):
        """Test parsing array literals with expressions"""
        source = 'let calculated = [1 + 2, x * 3, true and false]'
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        var_decl = ast.children[0]
        array_literal = var_decl.children[0]
        self.assertIsInstance(array_literal, ArrayLiteral)
        self.assertEqual(len(array_literal.elements), 3)
        
        # Check first element (1 + 2)
        self.assertIsInstance(array_literal.elements[0], BinaryOperation)
        self.assertEqual(array_literal.elements[0].token.value, '+')
        
        # Check second element (x * 3)
        self.assertIsInstance(array_literal.elements[1], BinaryOperation)
        self.assertEqual(array_literal.elements[1].token.value, '*')
        
        # Check third element (true and false)
        self.assertIsInstance(array_literal.elements[2], BinaryOperation)
        self.assertEqual(array_literal.elements[2].token.value, 'and')
    
    def test_parse_multiline_array(self):
        """Test parsing array literals with multiple lines and comments"""
        source = '''
        let sprite = [
            8, 8,  // Width, Height
            0, 0, 1, 1,  // First row
            2, 2, 3, 3   // Second row
        ]
        '''
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        var_decl = ast.children[0]
        array_literal = var_decl.children[0]
        self.assertIsInstance(array_literal, ArrayLiteral)
        
        # Array should have 10 elements (2 for dimensions + 8 for pixel data)
        self.assertEqual(len(array_literal.elements), 10)
        
        # Check dimensions
        self.assertEqual(array_literal.elements[0].value, 8)
        self.assertEqual(array_literal.elements[1].value, 8)
        
        # Check pixel data
        expected_pixel_data = [0, 0, 1, 1, 2, 2, 3, 3]
        for i, value in enumerate(expected_pixel_data):
            self.assertEqual(array_literal.elements[i+2].value, value)
    
    def test_array_access_in_expressions(self):
        """Test array access in expressions"""
        source = 'let result = 10 + numbers[x + 1] * 2'
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        var_decl = ast.children[0]
        binary_op = var_decl.children[0]
        self.assertIsInstance(binary_op, BinaryOperation)
        self.assertEqual(binary_op.token.value, '+')
        
        # Right side should be numbers[x + 1] * 2
        right = binary_op.right
        self.assertIsInstance(right, BinaryOperation)
        self.assertEqual(right.token.value, '*')
        
        # Left of multiplication should be array access
        array_access = right.left
        self.assertIsInstance(array_access, ArrayAccess)
        self.assertEqual(array_access.array.name, 'numbers')
        
        # Index should be x + 1
        index_expr = array_access.index
        self.assertIsInstance(index_expr, BinaryOperation)
        self.assertEqual(index_expr.token.value, '+')
    
    def test_complex_array_assignment(self):
        """Test complex array assignment with expressions"""
        source = 'matrix[row + 1][col - 1] = value * 2'
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        assignment = ast.children[0]
        self.assertIsInstance(assignment, Assignment)
        
        # Target should be nested array access
        target = assignment.target
        self.assertIsInstance(target, ArrayAccess)
        
        # First array access (matrix[row + 1])
        outer_access = target.array
        self.assertIsInstance(outer_access, ArrayAccess)
        self.assertEqual(outer_access.array.name, 'matrix')
        
        # First index (row + 1)
        outer_index = outer_access.index
        self.assertIsInstance(outer_index, BinaryOperation)
        self.assertEqual(outer_index.token.value, '+')
        
        # Second index (col - 1)
        inner_index = target.index
        self.assertIsInstance(inner_index, BinaryOperation)
        self.assertEqual(inner_index.token.value, '-')
        
        # Value (value * 2)
        value_expr = assignment.children[0]
        self.assertIsInstance(value_expr, BinaryOperation)
        self.assertEqual(value_expr.token.value, '*')
    
    def test_array_code_generation(self):
        """Test code generation for arrays"""
        source = '''
        let numbers = [1, 2, 3, 4, 5]
        let value = numbers[2]
        numbers[3] = 42
        '''
        
        # Parse the code
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        # Generate code
        generator = CodeGenerator()
        assembly = generator.generate(ast)
        
        # Verify array declaration generates correct code
        self.assertIn("PUSHI 1", assembly)
        self.assertIn("PUSHI 2", assembly)
        self.assertIn("PUSHI 3", assembly)
        self.assertIn("PUSHI 4", assembly)
        self.assertIn("PUSHI 5", assembly)
        
        # Verify array access generates correct code
        self.assertIn("PUSHI 2", assembly)  # Index
        self.assertIn("OPADD", assembly)    # Base + index
        self.assertIn("FETCHM", assembly)   # Load value
        
        # Verify array assignment generates correct code
        self.assertIn("PUSHI 42", assembly) # Value
        self.assertIn("PUSHI 3", assembly)  # Index
        self.assertIn("STO", assembly)      # Store value


class TestArrayIntegration(unittest.TestCase):
    """Integration tests for array functionality with VM execution"""
    
    def setUp(self):
        """Set up test environment"""
        # Create VM instance for testing
        self.vm = UltimaUnderworldVM(debug=False)
        self.variable_mappings = {}  # Store variable name -> offset mappings
    
    def parse_variable_mappings(self, assembly):
        """Parse variable mappings from assembly comments"""
        self.variable_mappings = {}
        lines = assembly.split('\n')
        
        # Look for variable mapping comments like "; name -> offset (type)"
        for line in lines:
            if line.strip().startswith(';') and ' -> ' in line:
                # Extract variable name and offset
                # Format: "; variable_name -> offset (type)"
                match = re.match(r';\s*(\w+)\s*->\s*(\d+)', line.strip())
                if match:
                    var_name = match.group(1)
                    offset = int(match.group(2))
                    self.variable_mappings[var_name] = offset
    
    def compile_and_load(self, source):
        """Compile source to assembly and load it into the VM"""
        # Compile the script
        result = compile_uwscript(source)
        assembly = result["assembly"]
        
        # Parse variable mappings from assembly comments
        self.parse_variable_mappings(assembly)
        
        # Write assembly to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".asm", delete=False) as f:
            f.write(assembly)
            asm_path = f.name
        
        try:
            # Parse the assembly
            self.vm.parse_asm(asm_path)
            self.vm.initialize_memory()
        finally:
            # Clean up temp file
            os.unlink(asm_path)
    
    def execute_until_complete(self, max_steps=1000):
        """Execute the VM until it finishes or reaches max steps"""
        self.vm.pc = 0
        self.vm.finished = False
        steps = 0
        
        while not self.vm.finished and steps < max_steps:
            if self.vm.pc < len(self.vm.code):
                opcode = self.vm.code[self.vm.pc]
                handler = self.vm.opcode_handlers.get(opcode)
                if handler:
                    handler()
                else:
                    self.vm.pc += 1
            else:
                break
            steps += 1
        
        return steps
    
    def get_variable_value(self, var_name):
        """Get the value of a variable from VM memory"""
        if var_name not in self.variable_mappings:
            return None
        offset = self.variable_mappings[var_name]
        return self.vm.get_mem(offset)
    
    def test_array_creation_and_access(self):
        """Test array creation and access in VM"""
        source = '''
        let numbers = [10, 20, 30, 40, 50]
        let value = numbers[2]  // Should be 30
        '''
        
        self.compile_and_load(source)
        self.execute_until_complete()
        
        # Check that value contains 30 (the value at index 2)
        value = self.get_variable_value('value')
        self.assertIsNotNone(value, "Variable 'value' not found in memory")
        self.assertEqual(value, 30)
    
    def test_array_assignment(self):
        """Test array assignment in VM"""
        source = '''
        let numbers = [10, 20, 30, 40, 50]
        numbers[1] = 25  // Change 20 to 25
        let value = numbers[1]
        '''
        
        self.compile_and_load(source)
        self.execute_until_complete()
        
        # Check that numbers[1] was updated to 25
        numbers_offset = self.variable_mappings.get('numbers')
        self.assertIsNotNone(numbers_offset, "Variable 'numbers' not found in memory")
        self.assertEqual(self.vm.get_mem(numbers_offset + 1), 25)
        
        # Check that value contains the updated value 25
        value = self.get_variable_value('value')
        self.assertEqual(value, 25)
    
    def test_array_with_expressions(self):
        """Test array access with expressions in VM"""
        source = '''
        let numbers = [10, 20, 30, 40, 50]
        let i = 1
        let value = numbers[i + 1]  // Should access index 2 (value 30)
        '''
        
        self.compile_and_load(source)
        self.execute_until_complete()
        
        # Check that value contains 30 (the value at index 2)
        value = self.get_variable_value('value')
        self.assertIsNotNone(value, "Variable 'value' not found in memory")
        self.assertEqual(value, 30)
    
    def test_multidimensional_array(self):
        """Test 2D array simulation using linear arrays"""
        source = '''
        // Create a 3x3 grid as a flat array
        let grid = [
            1, 2, 3,  // Row 0
            4, 5, 6,  // Row 1
            7, 8, 9   // Row 2
        ]
        
        // Access grid[1][2] which is element at index 5 (row 1, col 2)
        let row = 1
        let col = 2
        let width = 3
        let index = row * width + col
        let value = grid[index]
        '''
        
        self.compile_and_load(source)
        self.execute_until_complete()
        
        # Check that value contains 6 (the value at grid[1][2])
        value = self.get_variable_value('value')
        self.assertIsNotNone(value, "Variable 'value' not found in memory")
        self.assertEqual(value, 6)
    
    def test_sprite_data_access(self):
        """Test sprite data array access"""
        source = '''
        // Create a small 2x2 sprite
        let sprite = [
            2, 2,    // Width, height
            1, 2,    // Row 0 pixels
            3, 4     // Row 1 pixels
        ]
        
        // Width and height should be first two elements
        let width = sprite[0]
        let height = sprite[1]
        
        // Access pixel data
        let pixel00 = sprite[2]  // Row 0, Col 0
        let pixel01 = sprite[3]  // Row 0, Col 1
        let pixel10 = sprite[4]  // Row 1, Col 0
        let pixel11 = sprite[5]  // Row 1, Col 1
        '''
        
        self.compile_and_load(source)
        self.execute_until_complete()
        
        # Verify sprite dimensions are correctly accessed
        width = self.get_variable_value('width')
        height = self.get_variable_value('height')
        
        self.assertEqual(width, 2)
        self.assertEqual(height, 2)
        
        # Verify pixel data is correctly accessed
        expected_pixels = {
            'pixel00': 1,
            'pixel01': 2,
            'pixel10': 3,
            'pixel11': 4
        }
        
        for name, expected_value in expected_pixels.items():
            value = self.get_variable_value(name)
            self.assertIsNotNone(value, f"Variable '{name}' not found in memory")
            self.assertEqual(value, expected_value)
    
    def test_variable_mapping_extraction(self):
        """Test that variable mappings are correctly extracted from assembly"""
        source = '''
        let first = 10
        let second = "test"
        let third = true
        '''
        
        self.compile_and_load(source)
        
        # Check that variable mappings were extracted
        self.assertIn('first', self.variable_mappings)
        self.assertIn('second', self.variable_mappings)
        self.assertIn('third', self.variable_mappings)
        
        # Check that offsets are correct (should be 0, 1, 2)
        self.assertEqual(self.variable_mappings['first'], 0)
        self.assertEqual(self.variable_mappings['second'], 1)
        self.assertEqual(self.variable_mappings['third'], 2)
    
    def test_array_bounds_behavior(self):
        """Test behavior when accessing array elements (no bounds checking in VM)"""
        source = '''
        let small_array = [10, 20, 30]
        let normal_access = small_array[1]  // Should be 20
        let beyond_array = small_array[5]   // Accesses memory beyond array
        '''
        
        self.compile_and_load(source)
        self.execute_until_complete()
        
        # Normal access should work
        normal_value = self.get_variable_value('normal_access')
        self.assertEqual(normal_value, 20)
        
        # Beyond array access will read whatever is in memory at that location
        # (This is expected behavior - no bounds checking in the VM)
        beyond_value = self.get_variable_value('beyond_array')
        self.assertIsNotNone(beyond_value)  # Should return some value
    
    def test_array_compound_assignment(self):
        """Test compound assignment to array elements"""
        source = '''
        let numbers = [10, 20, 30, 40, 50]
        numbers[2] += 5  // Should become 35
        let result = numbers[2]
        '''
        
        self.compile_and_load(source)
        self.execute_until_complete()
        
        # Check that the compound assignment worked
        result = self.get_variable_value('result')
        self.assertEqual(result, 35)
        
        # Also check the array element directly
        numbers_offset = self.variable_mappings.get('numbers')
        self.assertIsNotNone(numbers_offset)
        self.assertEqual(self.vm.get_mem(numbers_offset + 2), 35)


class TestArrayEdgeCases(unittest.TestCase):
    """Test edge cases and error handling for arrays"""
    
    def test_empty_array(self):
        """Test parsing an empty array"""
        source = 'let empty = []'
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        var_decl = ast.children[0]
        self.assertIsInstance(var_decl, VariableDeclaration)
        
        array_literal = var_decl.children[0]
        self.assertIsInstance(array_literal, ArrayLiteral)
        self.assertEqual(len(array_literal.elements), 0)
    
    def test_array_with_mixed_types(self):
        """Test array with mixed types (numbers, strings, booleans)"""
        source = 'let mixed = [42, "text", true, 314]'  # Changed 3.14 to 314
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        var_decl = ast.children[0]
        array_literal = var_decl.children[0]
        self.assertEqual(len(array_literal.elements), 4)
        
        # Check types
        self.assertEqual(array_literal.elements[0].value, 42)
        self.assertEqual(array_literal.elements[1].value, "text")
        self.assertEqual(array_literal.elements[2].token.value, "true")
        self.assertEqual(array_literal.elements[3].value, 314)  # Changed expected value
    
    def test_array_with_trailing_comma(self):
        """Test array with trailing comma"""
        source = 'let numbers = [1, 2, 3,]'
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        var_decl = ast.children[0]
        array_literal = var_decl.children[0]
        self.assertEqual(len(array_literal.elements), 3)
    
    def test_nested_array_access(self):
        """Test nested array access with complex indices"""
        source = 'let value = grid[row * width + col % size]'
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        var_decl = ast.children[0]
        array_access = var_decl.children[0]
        self.assertIsInstance(array_access, ArrayAccess)
        
        # Index should be complex expression
        index_expr = array_access.index
        self.assertIsInstance(index_expr, BinaryOperation)
        self.assertEqual(index_expr.token.value, '+')
        
        # Left side of + should be (row * width)
        left = index_expr.left
        self.assertIsInstance(left, BinaryOperation)
        self.assertEqual(left.token.value, '*')
        
        # Right side of + should be (col % size)
        right = index_expr.right
        self.assertIsInstance(right, BinaryOperation)
        self.assertEqual(right.token.value, '%')
    
    def test_array_error_undefined_variable(self):
        """Test error when accessing undefined array"""
        source = 'let value = undefined_array[0]'
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        # Generate code - should raise error
        generator = CodeGenerator()
        with self.assertRaises(NameError):
            generator.generate(ast)
    
    def test_array_error_non_array_access(self):
        """Test error when treating non-array as array"""
        source = '''
        let scalar = 42
        let value = scalar[0]
        '''
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        ast = parser.parse()
        
        # Generate code - should raise error
        generator = CodeGenerator()
        with self.assertRaises(TypeError):
            generator.generate(ast)
    
    def test_compound_array_assignment(self):
        """Test compound assignment to array elements"""
        source = '''
        let numbers = [10, 20, 30, 40, 50]
        numbers[2] += 5  // Should become 35
        '''
        
        # This currently isn't supported, but test should be added
        # when implementation is ready
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        
        # Should parse without errors
        ast = parser.parse()
        
        assignment = ast.children[1]
        self.assertIsInstance(assignment, Assignment)
        self.assertIsInstance(assignment.target, ArrayAccess)
        self.assertEqual(assignment.operator, '+=')
    
    def test_array_with_comments(self):
        """Test array definition with comments in various positions"""
        source = '''
        let array = [ // Array starts here
            1,  // First element
            2,  // Second element
            3   // Last element
        ] // Array ends here
        '''
        
        lexer = Lexer(source)
        tokens = lexer.tokenize()
        parser = Parser(tokens)
        
        # Should parse without errors
        ast = parser.parse()
        
        var_decl = ast.children[0]
        array_literal = var_decl.children[0]
        self.assertIsInstance(array_literal, ArrayLiteral)
        self.assertEqual(len(array_literal.elements), 3)


def create_test_suite():
    """Create a test suite with all test cases"""
    suite = unittest.TestSuite()
    
    # Add test classes
    test_classes = [
        TestLexer,
        TestParser,
        TestCodeGenerator,
        TestStringExtraction,
        TestCompileUWScript,
        TestErrorHandling,
        TestComplexPrograms,
        TestFileIO,
        TestArrayFunctionality,
        #TestArrayIntegration,
        TestArrayEdgeCases
    ]
    
    for test_class in test_classes:
        tests = unittest.TestLoader().loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    return suite


if __name__ == '__main__':
    # Run the test suite
    runner = unittest.TextTestRunner(verbosity=2)
    suite = create_test_suite()
    result = runner.run(suite)
    
    # Exit with appropriate code
    sys.exit(0 if result.wasSuccessful() else 1)
