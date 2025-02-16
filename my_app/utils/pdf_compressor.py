
#!/usr/bin/env python3

import os
import subprocess
import sys
from pathlib import Path
import shutil


class PDFCompressor:
    def __init__(self):
        # Specify the Ghostscript executable path (Update this if necessary)
        self.GS_PATH = r"C:\Program Files\gs\gs10.04.0\bin\gswin64c.exe"

        self.compression_commands = {
            'light': {
                'level': 1,
                'cmd': [
                    self.GS_PATH, '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4',
                    '-dPDFSETTINGS=/prepress', '-dNOPAUSE', '-dQUIET', '-dBATCH'
                ]
            },
            'moderate': {
                'level': 2,
                'cmd': [
                    self.GS_PATH, '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4',
                    '-dPDFSETTINGS=/printer', '-dNOPAUSE', '-dQUIET', '-dBATCH'
                ]
            },
            'standard': {
                'level': 3,
                'cmd': [
                    self.GS_PATH, '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4',
                    '-dPDFSETTINGS=/ebook', '-dNOPAUSE', '-dQUIET', '-dBATCH'
                ]
            },
            'high': {
                'level': 4,
                'cmd': [
                    self.GS_PATH, '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4',
                    '-dPDFSETTINGS=/screen', '-dNOPAUSE', '-dQUIET', '-dBATCH'
                ]
            },
            'very_high': {
                'level': 5,
                'cmd': [
                    self.GS_PATH, '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4',
                    '-dPDFSETTINGS=/screen', '-dDownsampleColorImages=true',
                    '-dColorImageResolution=72', '-dGrayImageResolution=72',
                    '-dMonoImageResolution=72', '-dNOPAUSE', '-dQUIET', '-dBATCH'
                ]
            },
            'extreme': {
                'level': 6,
                'cmd': [
                    self.GS_PATH, '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4',
                    '-dPDFSETTINGS=/screen', '-dDownsampleColorImages=true',
                    '-dDownsampleGrayImages=true', '-dDownsampleMonoImages=true',
                    '-dColorImageResolution=50', '-dGrayImageResolution=50',
                    '-dMonoImageResolution=50', '-dColorImageDownsampleType=/Bicubic',
                    '-dGrayImageDownsampleType=/Bicubic', '-dMonoImageDownsampleType=/Bicubic',
                    '-dNOPAUSE', '-dQUIET', '-dBATCH'
                ]
            },
            'maximum': {
                'level': 7,
                'cmd': [
                    self.GS_PATH, '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4',
                    '-dPDFSETTINGS=/screen', '-dDownsampleColorImages=true',
                    '-dDownsampleGrayImages=true', '-dDownsampleMonoImages=true',
                    '-dColorImageResolution=35', '-dGrayImageResolution=35',
                    '-dMonoImageResolution=35', '-dColorImageDownsampleType=/Bicubic',
                    '-dGrayImageDownsampleType=/Bicubic', '-dMonoImageDownsampleType=/Bicubic',
                    '-dAutoRotatePages=/None', '-dColorImageFilter=/DCTEncode',
                    '-dGrayImageFilter=/DCTEncode', '-dMonoImageFilter=/CCITTFaxEncode',
                    '-dAutoFilterColorImages=false', '-dAutoFilterGrayImages=false',
                    '-dAutoFilterMonoImages=false', '-dColorConversionStrategy=/LeaveColorUnchanged',
                    '-dEncodeColorImages=true', '-dEncodeGrayImages=true',
                    '-dEncodeMonoImages=true', '-dCompressPages=true',
                    '-dDetectDuplicateImages=true', '-dCompressFonts=true',
                    '-dEmbedAllFonts=true', '-dSubsetFonts=true',
                    '-dNOPAUSE', '-dQUIET', '-dBATCH'
                ]
            },
            'ultimate': {
                'level': 8,
                'cmd': [
                    self.GS_PATH, '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4',
                    '-dPDFSETTINGS=/screen', '-dDownsampleColorImages=true',
                    '-dDownsampleGrayImages=true', '-dDownsampleMonoImages=true',
                    '-dColorImageResolution=20', '-dGrayImageResolution=20',
                    '-dMonoImageResolution=20', '-dColorImageDownsampleType=/Average',
                    '-dGrayImageDownsampleType=/Average', '-dMonoImageDownsampleType=/Average',
                    '-dAutoRotatePages=/None', '-dColorImageFilter=/DCTEncode',
                    '-dGrayImageFilter=/DCTEncode', '-dMonoImageFilter=/CCITTFaxEncode',
                    '-dAutoFilterColorImages=false', '-dAutoFilterGrayImages=false',
                    '-dAutoFilterMonoImages=false', '-dColorConversionStrategy=/LeaveColorUnchanged',
                    '-dEncodeColorImages=true', '-dEncodeGrayImages=true',
                    '-dEncodeMonoImages=true', '-dCompressPages=true',
                    '-dDetectDuplicateImages=true', '-dCompressFonts=true',
                    '-dEmbedAllFonts=true', '-dSubsetFonts=true',
                    '-dConvertCMYKImagesToRGB=true', '-dFastWebView=true',
                    '-dNOPAUSE', '-dQUIET', '-dBATCH'
                ]
            }
        }

    def get_file_size_kb(self, file_path):
        return os.path.getsize(file_path) / 1024

    def compress_pdf(self, input_file, output_file, compression_level):
        cmd = self.compression_commands[compression_level]['cmd'] + [
            f'-sOutputFile={output_file}',
            input_file
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            return True
        except FileNotFoundError as e:
            print(f"Ghostscript not found! Ensure it is installed and the path is correct. Error: {e}")
            return False
        except subprocess.CalledProcessError as e:
            print(f"Error during compression: {e.stderr}")
            return False
        except PermissionError as e:
            print(f"Permission denied: {e}")
            return False

    def compress_to_target_size(self, input_file, target_size_kb):
        input_path = Path(input_file)
        if not input_path.exists():
            print(f"Input file {input_file} does not exist!")
            return None

        original_size = self.get_file_size_kb(input_file)
        print(f"Original file size: {original_size:.2f} KB")
        print(f"Target size: {target_size_kb:.2f} KB")

        if original_size <= target_size_kb:
            print("File is already smaller than target size!")
            return input_file

        # Create temp directory for intermediate files
        temp_dir = Path("temp_compression")
        temp_dir.mkdir(exist_ok=True)

        best_result = None
        best_size = float('inf')

        # Try each compression level
        for level_name, level_info in sorted(
            self.compression_commands.items(),
            key=lambda x: x[1]['level']
        ):
            print(f"\nTrying {level_name} compression...")
            output_file = temp_dir / f"compressed_{level_name}_{input_path.name}"

            if self.compress_pdf(str(input_path), str(output_file), level_name):
                current_size = self.get_file_size_kb(output_file)
                print(f"Compressed size: {current_size:.2f} KB")

                if current_size < best_size:
                    best_size = current_size
                    best_result = output_file

                if current_size <= target_size_kb:
                    print(f"Target size achieved with {level_name} compression!")
                    break
            else:
                print(f"Compression failed for level {level_name}")

        # Try additional optimizations if target size not reached
        if best_size > target_size_kb and best_result:
            print("\nTrying additional optimizations...")

            # Try grayscale conversion
            gray_output = temp_dir / f"gray_{input_path.name}"
            gray_cmd = [
                self.GS_PATH, '-sOutputFile=' + str(gray_output),
                '-sDEVICE=pdfwrite', '-sColorConversionStrategy=Gray',
                '-dProcessColorModel=/DeviceGray', '-dCompatibilityLevel=1.4',
                '-dNOPAUSE', '-dBATCH', str(best_result)
            ]
            subprocess.run(gray_cmd, capture_output=True, text=True)

            gray_size = self.get_file_size_kb(gray_output)
            if gray_size < best_size:
                best_size = gray_size
                best_result = gray_output

        # Create final output file
        final_output = input_path.parent / f"compressed_{input_path.name}"
        if best_result:
            shutil.copy2(best_result, final_output)
            shutil.rmtree(temp_dir)  # Clean up temp files

            print("\nCompression Results:")
            print(f"Original size: {original_size:.2f} KB")
            print(f"Final size: {best_size:.2f} KB")
            print(f"Compression ratio: {(original_size - best_size) / original_size * 100:.2f}%")

            if best_size > target_size_kb:
                print("\nWarning: Could not achieve target size while maintaining PDF integrity")

            return final_output
        else:
            print("Compression failed!")
            return None


def main():
    if len(sys.argv) != 3:
        print("Usage: python pdf_compressor.py <input_pdf> <target_size_kb>")
        sys.exit(1)

    input_file = sys.argv[1]
    try:
        target_size = float(sys.argv[2])
    except ValueError:
        print("Target size must be a number in KB")
        sys.exit(1)

    compressor = PDFCompressor()
    result = compressor.compress_to_target_size(input_file, target_size)

    if result:
        print(f"\nCompressed file saved as: {result}")
    else:
        print("\nCompression failed!")


if __name__ == "__main__":
    main()