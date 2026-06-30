#!/usr/bin/env python3
"""
Translation Script for QATrack+
Translates .po files to a target language.
"""

import re
import subprocess
import sys
import time
from pathlib import Path

import polib

# Google Translate setup
try:
    from googletrans import Translator
    GOOGLE_TRANSLATE_AVAILABLE = True
except ImportError:
    GOOGLE_TRANSLATE_AVAILABLE = False


def find_po_files(language_code=None):
    """Find all .po files, filtered by language code"""
    po_files = []
    locale_dir = Path('qatrack/locale')
    
    if language_code:
        po_file = locale_dir / language_code / 'LC_MESSAGES' / 'django.po'
        if po_file.exists():
            po_files.append(po_file)
    else:
        # Find all .po files
        for lang_dir in locale_dir.iterdir():
            if lang_dir.is_dir():
                po_file = lang_dir / 'LC_MESSAGES' / 'django.po'
                if po_file.exists():
                    po_files.append(po_file)
    
    return po_files


def should_skip_translation(msgid):
    """Determine if a string should be skipped from translation"""
    if not msgid or not msgid.strip():
        return True
    
    # Skip pure format variables (e.g., %(name)s, %s, {variable})
    if re.fullmatch(r'\s*%\([^)]+\)[a-z]\s*', msgid):
        return True
    if re.fullmatch(r'\s*%[a-z]\s*', msgid):
        return True
    if re.fullmatch(r'\s*\{[^}]+\}\s*', msgid):
        return True
    
    # Skip strings that are just punctuation or numbers
    if re.fullmatch(r'\s*[^\w\s]+\s*', msgid):
        return True
    if re.fullmatch(r'\s*\d+\s*', msgid):
        return True
    
    # Skip very short strings (likely not translatable)
    if len(msgid.strip()) <= 2:
        return True
    
    return False


def translate_po_file(po_file_path, target_language='es', source_language='en'):
    """Translate a .po file while preserving format variables"""
    
    if not GOOGLE_TRANSLATE_AVAILABLE:
        print("❌ Google Translate library not available. Install with: uv pip install googletrans==4.0.0rc1")
        return False
    
    print(f"🌐 Translating {po_file_path} to {target_language}...")
    
    # Read the PO file
    po = polib.pofile(str(po_file_path))
    translator = Translator()
    
    # Track translation progress
    total_entries = len([e for e in po if not e.obsolete])
    translated_entries = 0
    skipped_entries = 0
    failed_translations = []
    
    for entry in po:
        if entry.obsolete:
            continue
        
        # Skip entries that shouldn't be translated
        if should_skip_translation(entry.msgid):
            entry.msgstr = entry.msgid
            skipped_entries += 1
            continue
        
        # Skip if already has a translation
        if entry.msgstr and entry.msgstr.strip():
            continue
        
        # Translate the string
        try:
            # Add delay to avoid rate limiting
            time.sleep(0.5)
            
            translation = translator.translate(entry.msgid, src=source_language, dest=target_language)
            
            if translation and translation.text:
                entry.msgstr = translation.text
                translated_entries += 1
            else:
                # Fallback to original if translation failed
                entry.msgstr = entry.msgid
                failed_translations.append(entry.msgid)
                
        except Exception as e:
            print(f"   ⚠️  Failed to translate '{entry.msgid[:50]}...': {str(e)[:100]}")
            entry.msgstr = entry.msgid
            failed_translations.append(entry.msgid)
        
        # Progress indicator
        if (translated_entries + skipped_entries) % 25 == 0:
            print(f"   Progress: {translated_entries + skipped_entries}/{total_entries}")
    
    # Save the translated file
    po.save(str(po_file_path))
    
    print("✅ Translation completed:")
    print(f"   Translated: {translated_entries}")
    print(f"   Skipped: {skipped_entries}")
    print(f"   Failed: {len(failed_translations)}")
    
    return True


def compile_messages():
    """Compile all .po files to .mo format"""
    try:
        result = subprocess.run(['python', 'manage.py', 'compilemessages'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Messages compiled successfully")
            return True
        else:
            print(f"❌ Error compiling messages: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ Error compiling messages: {e}")
        return False


def list_available_languages():
    """List all available language codes with existing .po files"""
    po_files = find_po_files()
    if not po_files:
        print("❌ No .po files found in qatrack/locale/")
        return
    
    print("📋 Available languages with .po files:")
    for po_file in po_files:
        lang_code = po_file.parent.parent.name
        print(f"   {lang_code}: {po_file}")


def main():
    """Main function to run the translation process"""
    
    if len(sys.argv) < 2:
        print("""
🌐 Simple Translation Manager for QATrack+

This script translates .po files while preserving format variables.

Usage:
  python scripts/translation.py <command> [language_code]

Commands:
  list                    - List available languages with .po files
  translate <lang>        - Translate .po file for specified language
  compile                - Compile all .po files to .mo format
  all <lang>             - Translate and compile for specified language

Examples:
  python scripts/translation.py list
  python scripts/translation.py translate es
  python scripts/translation.py all es
  python scripts/translation.py compile

Supported language codes: fr, es, de, it, pt, zh, ja, ko, ru, etc.
        """)
        return

    command = sys.argv[1]

    if command == 'list':
        list_available_languages()
        return
    
    if command == 'compile':
        print("🔄 Compiling messages...")
        compile_messages()
        return

    # Commands that require a language code
    if len(sys.argv) < 3:
        print("❌ Language code required for this command")
        print("Usage: python scripts/translation.py <command> <language_code>")
        return
    
    language_code = sys.argv[2]
    po_file = Path(f'qatrack/locale/{language_code}/LC_MESSAGES/django.po')
    
    if not po_file.exists():
        print(f"❌ PO file not found: {po_file}")
        print(f"Generate it first with: python manage.py makemessages -l {language_code}")
        return

    if command == 'translate':
        print(f"🔄 Starting translation for language: {language_code}")
        translate_po_file(po_file, language_code)
        
    elif command == 'all':
        print(f"🔄 Starting complete translation process for language: {language_code}")
        translate_po_file(po_file, language_code)
        compile_messages()
        print(f"✅ Complete translation process finished for {language_code}!")
        
    else:
        print(f"❌ Unknown command: {command}")
        print("Valid commands: list, translate, compile, all")


if __name__ == "__main__":
    main()
