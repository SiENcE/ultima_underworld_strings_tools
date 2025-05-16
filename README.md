# Ultima Underworld STRINGS.PAK Tools

A collection of Python utilities for analyzing, extracting, and repacking the STRINGS.PAK file from Ultima Underworld games, as well as working with conversation scripts from CNV.ARK. These tools allow you to examine the structure of game files, extract content, modify strings, and even run conversation scripts.

## Tools Included

1. **uw-strings-analyzer.py** - Analyzes the structure of STRINGS.PAK, showing the Huffman tree, block information, and more
2. **uw-strings-extractor.py** - Extracts all strings from STRINGS.PAK into a text file
3. **uw-strings-packer.py** - Repacks modified strings back into a new STRINGS.PAK file
4. **uw-strings-translator.py** - Tool for translating Ultima Underworld game text strings using Ollama (for local LLM translation) or Transformers (using Hugging Face's translation models) (more [README_translator.md](/README_translator.md) )
5. **uw_cnv_extractor_decompress_decompiler.py** - Extracts, decompresses, and decompiles conversation scripts from CNV.ARK
6. **uw_cnv_runner.py** - Virtual machine for executing and interacting with the conversation scripts 

## Requirements

- Python 3.6 or higher

## Installation

Clone this repository or download the scripts:

```bash
git clone https://github.com/yourusername/uw-strings-tools.git
cd uw-strings-tools
```

## Usage

### 1. Analyzing STRINGS.PAK

Use the analyzer to examine the structure of your STRINGS.PAK file:

```bash
python uw-strings-analyzer.py path/to/strings.pak
```

Optional hexdump feature:

```bash
python uw-strings-analyzer.py path/to/strings.pak --hexdump [offset] [length]
```

This will generate a detailed analysis including:
- File header information
- Huffman tree structure
- Block information
- String encoding samples
- File integrity check

The analysis will also be exported to a `strings-analysis.json` file.

### 2. Extracting Strings

To extract all strings from STRINGS.PAK to a text file:

```bash
python uw-strings-extractor.py
```

This assumes `strings.pak` is in the current directory. It will:
- Extract all strings into `uw-strings.txt`
- Save Huffman tree and block metadata to `uw-strings-metadata.json` (needed for repacking)

The extracted file format is:

```
STRINGS.PAK: 123 string blocks.

block: 0001; 15 strings.
0: This is string 0
1: This is string 1
...

block: 0002; 8 strings.
0: Another block string
...
```

### 3. Modifying and Repacking Strings

1. Edit the extracted `uw-strings.txt` file with any text editor
2. Run the packer to create a new STRINGS.PAK file:

```bash
python uw-strings-packer.py
```

The packer will:
- Read the Huffman tree from `uw-strings-metadata.json`
- Parse the modified `uw-strings.txt` file
- Create a new `strings.pak` file
- Verify the created file is readable
- Compare with an original file if available (`original_strings.pak`)

### 4. Extracting and Decompiling CNV.ARK

Extract conversation scripts from CNV.ARK and decompile them to assembly:

```bash
python uw_cnv_extractor_decompress_decompiler.py path/to/CNV.ARK -o output_directory -v
```

This will:
- Extract all conversation slots from CNV.ARK
- Decompress the data if it's compressed
- Decompile the bytecode to human-readable assembly
- Generate binary files (.bin), metadata (.txt), and assembly code (.asm) for each conversation

The output directory will contain files named `conversation_XXXX.bin`, `conversation_XXXX.txt`, and `conversation_XXXX.asm` where XXXX is the slot ID in hexadecimal.

### 5. Running Conversation Scripts

Run the extracted conversation scripts using the conversation VM:

```bash
python uw_cnv_runner.py path/to/conversation_XXXX.asm --strings path/to/uw-strings.txt --debug
```

This will:
- Load the specified conversation assembly code
- Load the string block referenced by the conversation
- Execute the conversation script
- Simulate NPC dialogue and player responses
- Allow you to interact with the conversation through prompts

The conversation runner provides a virtual machine that simulates the game's conversation system, allowing you to test and explore dialogue trees.

## Notes on Editing Strings

When modifying the extracted strings:
- Keep the `block:` and string index format intact
- You can modify the content of each string
- Use `\n` for line breaks
- Don't remove the ending pipe character (`|`) if present
- Adding new blocks or changing block IDs is not recommended

## Technical Details

STRINGS.PAK uses Huffman compression with the following structure:
- File header with Huffman tree nodes
- Block info table with block IDs and offsets
- Multiple string blocks containing:
  - String count
  - String offset table
  - Huffman-encoded string data

CNV.ARK contains conversation scripts with the following components:
- Header with metadata and import information
- Bytecode for the conversation VM
- References to strings in STRINGS.PAK

## License

This project is licensed under the MIT License with additional terms - see the [LICENSE](LICENSE) file for details.
**Important:** Use of this software for training AI or machine learning models is strictly prohibited. See the LICENSE file for details.

## Credits

Copyright (c) 2025 Florian Fischer
