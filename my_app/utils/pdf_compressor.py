
#!/usr/bin/env python3
#  self.GS_PATH =  'gs' # r"C:\Program Files\gs\gs10.04.0\bin\gswin64c.exe" #'gs'
#!/usr/bin/env python3

import os
import subprocess
from pathlib import Path
import shutil
import tempfile

class PDFCompressor:
    def __init__(self):
        self.GS_PATH = self._find_ghostscript()
        self.timeout = 120  # seconds
        
    def _find_ghostscript(self):
        """Try to locate Ghostscript executable"""
        for gs_cmd in ['gs', 'gswin64c', 'gswin32c']:
            try:
                subprocess.run([gs_cmd, '--version'], check=True, 
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return gs_cmd
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue
        raise RuntimeError("Ghostscript not found. Please install Ghostscript")

    def get_file_size_kb(self, file_path):
        return os.path.getsize(file_path) / 1024

    def _run_ghostscript(self, cmd, input_file):
        """Run Ghostscript with robust error handling"""
        try:
            result = subprocess.run(
                cmd,
                check=True,
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                text=True,
                timeout=self.timeout
            )
            if result.stderr:
                print(f"Ghostscript warnings: {result.stderr}")
            return True
        except subprocess.TimeoutExpired:
            print(f"Timeout processing {input_file}")
            return False
        except subprocess.CalledProcessError as e:
            print(f"Ghostscript failed with: {e.stderr}")
            return False

    def compress_pdf(self, input_file, output_file, target_size_kb):
        """Improved compression with multiple fallback strategies"""
        input_path = Path(input_file)
        original_size = self.get_file_size_kb(input_file)
        
        if original_size <= target_size_kb:
            return input_file

        # Try different compression strategies in order
        strategies = [
            self._try_prepress_compression,
            self._try_printer_compression,
            self._try_ebook_compression,
            self._try_screen_compression
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            best_result = None
            best_size = original_size

            for strategy in strategies:
                output_path = temp_dir / f"compressed_{strategy.__name__}.pdf"
                if strategy(input_path, output_path):
                    current_size = self.get_file_size_kb(output_path)
                    
                    if current_size < best_size:
                        best_size = current_size
                        best_result = output_path
                        
                        if best_size <= target_size_kb:
                            break

            if best_result:
                shutil.copy2(best_result, output_file)
                return output_file

        return None

    def _try_prepress_compression(self, input_path, output_path):
        """High quality preservation"""
        cmd = [
            self.GS_PATH,
            '-dSAFER',
            '-dBATCH',
            '-dNOPAUSE',
            '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            '-dPDFSETTINGS=/prepress',
            '-dDetectDuplicateImages=true',
            '-dCompressFonts=true',
            '-dSubsetFonts=true',
            '-dAutoRotatePages=/None',
            f'-sOutputFile={output_path}',
            str(input_path)
        ]
        return self._run_ghostscript(cmd, input_path)

    def _try_printer_compression(self, input_path, output_path):
        """Good quality with better compression"""
        cmd = [
            self.GS_PATH,
            '-dSAFER',
            '-dBATCH',
            '-dNOPAUSE',
            '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            '-dPDFSETTINGS=/printer',
            '-dDetectDuplicateImages=true',
            '-dCompressFonts=true',
            '-dSubsetFonts=true',
            f'-sOutputFile={output_path}',
            str(input_path)
        ]
        return self._run_ghostscript(cmd, input_path)

    def _try_ebook_compression(self, input_path, output_path):
        """Medium quality with good compression"""
        cmd = [
            self.GS_PATH,
            '-dSAFER',
            '-dBATCH',
            '-dNOPAUSE',
            '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            '-dPDFSETTINGS=/ebook',
            '-dColorImageDownsampleType=/Bicubic',
            '-dGrayImageDownsampleType=/Bicubic',
            '-dColorImageResolution=150',
            '-dGrayImageResolution=150',
            f'-sOutputFile={output_path}',
            str(input_path)
        ]
        return self._run_ghostscript(cmd, input_path)

    def _try_screen_compression(self, input_path, output_path):
        """Lower quality with maximum compression"""
        cmd = [
            self.GS_PATH,
            '-dSAFER',
            '-dBATCH',
            '-dNOPAUSE',
            '-sDEVICE=pdfwrite',
            '-dCompatibilityLevel=1.4',
            '-dPDFSETTINGS=/screen',
            '-dColorImageDownsampleType=/Bicubic',
            '-dGrayImageDownsampleType=/Bicubic',
            '-dColorImageResolution=72',
            '-dGrayImageResolution=72',
            '-dMonoImageResolution=72',
            f'-sOutputFile={output_path}',
            str(input_path)
        ]
        return self._run_ghostscript(cmd, input_path)