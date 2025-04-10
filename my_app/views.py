

from datetime import datetime, time

from io import BytesIO
import json
import subprocess
# import tempfile
from django.http import FileResponse, HttpResponse, HttpResponseNotFound, JsonResponse
import pandas as pd
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
import os
import zipfile
from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import viewsets, status
import PyPDF2
from PIL import Image
# import numpy as np
# from django.utils.text import slugify
import pdfkit
# from openpyxl import Workbook
from django.contrib import messages 
# from fpdf import FPDF
# import speech_recognition as sr
# from pydub import AudioSegment

import shutil
from pathlib import Path
from django.core.files.base import ContentFile
from .utils.pdf_compressor import PDFCompressor

from Crypto.Cipher import AES
from Crypto.Protocol.KDF import PBKDF2
from Crypto.Util.Padding import unpad
from Crypto.Hash import SHA256, HMAC
from .utils.encryption import EncryptionMixin



class FileOperationsViewSet(EncryptionMixin, viewsets.ViewSet):

    # def generate_key(self, password):
    #     # This should match your JavaScript PBKDF2 settings
    #     salt = b"your-static-salt"  # Must match the salt used in JS
    #     iterations = 100000
    #     key = PBKDF2(password.encode(), salt, dkLen=32, count=iterations, prf=lambda p, s: HMAC.new(p, s, SHA256).digest())
    #     return key

    # def encrypt_file(self, data, password):
    #     # Generate key
    #     key = self.generate_key(password)
        
    #     # Generate random IV
    #     iv = os.urandom(12)
        
    #     # Encrypt
    #     cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    #     ciphertext, tag = cipher.encrypt_and_digest(data)
        
    #     # Combine IV and ciphertext
    #     encrypted_data = iv + ciphertext
        
    #     return encrypted_data
    
    # def decrypt_file(self, encrypted_data, password):
    #     # Extract IV (first 12 bytes)
    #     iv = encrypted_data[:12]
    #     ciphertext = encrypted_data[12:]
        
    #     # Generate key
    #     key = self.generate_key(password)
    #     print('key', key)
    #     # Decrypt
    #     cipher = AES.new(key, AES.MODE_GCM, nonce=iv)
    #     decrypted_data = cipher.decrypt(ciphertext)
        
    #     return decrypted_data

    def split_pdf(self, pdf_path, output_folder):
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            split_files = []
            for i in range(len(reader.pages)):
                writer = PyPDF2.PdfWriter()
                writer.add_page(reader.pages[i])

                output_filename = os.path.join(output_folder, f"page_{i + 1}.pdf")
                with open(output_filename, 'wb') as output_pdf:
                    writer.write(output_pdf)
                split_files.append(output_filename)
        return split_files
    
    @action(detail=False, methods=['post'])
    @EncryptionMixin.simple_encrypt
    def split_pdf_file(self, request):
        """Endpoint to handle PDF splitting with encryption/decryption."""
        uploaded_file = request.FILES.get('file')

        if not uploaded_file:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Create temporary working directory
            output_folder = os.path.join(settings.MEDIA_ROOT, "split_pdfs")
            os.makedirs(output_folder, exist_ok=True)
            
            # Get the decrypted file from request (handled by mixin)
            # The mixin has already decrypted the file at this point
            temp_pdf_path = os.path.join(output_folder, uploaded_file.name)
            
            # Save the decrypted file temporarily
            with open(temp_pdf_path, 'wb') as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)

            # Split the PDF into individual pages
            split_files = self.split_pdf(temp_pdf_path, output_folder)
            
            # Create zip file in memory (don't save to disk)
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in split_files:
                    with open(file, 'rb') as f:
                        file_data = f.read()
                    zipf.writestr(os.path.basename(file), file_data)
            
            # Clean up temporary files
            os.remove(temp_pdf_path)
            for file in split_files:
                os.remove(file)
            
            # Prepare response - will be encrypted by the mixin
            zip_buffer.seek(0)
            response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
            response['Content-Disposition'] = 'attachment; filename="split_pages.zip"'
            return response

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)   


    def merge_pdfs(self, pdf_files):
        merger = PyPDF2.PdfMerger()

        for pdf in pdf_files:
            merger.append(pdf)

        output_filename = 'merged_output.pdf'
        output_path = default_storage.path(output_filename)
        with open(output_path, 'wb') as output_pdf:
            merger.write(output_pdf)

        return output_path
    
    @action(detail=False, methods=['post'])
    @EncryptionMixin.simple_encrypt
    def mergePDF(self, request):
        # if request.method == 'POST':
        #     pdf_files = request.FILES.getlist('files')
        #     if not pdf_files:
        #         return JsonResponse({"error": "No files provided"}, status=400)
            
        #     try:
        #         merged_pdf_path = self.merge_pdfs(pdf_files)
        #     except Exception as e:
        #         return JsonResponse({"error": str(e)}, status=500)

        #     with open(merged_pdf_path, 'rb') as merged_pdf:
        #         response = HttpResponse(merged_pdf.read(), content_type='application/pdf')
        #         response['Content-Disposition'] = 'attachment; filename="merged_output.pdf"'
        #         return response
        pdf_files = request.FILES.getlist('files')
    
        if not pdf_files:
            return JsonResponse({"error": "No files provided"}, status=400)
        
        try:
            # Process decrypted files
            merged_pdf_path = self.merge_pdfs(pdf_files)
            
            # Response will be automatically encrypted by the mixin
            with open(merged_pdf_path, 'rb') as merged_pdf:
                response = HttpResponse(merged_pdf.read(), content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="merged_output.pdf"'
                return response
                
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
        finally:
            # Clean up temporary file
            if 'merged_pdf_path' in locals() and os.path.exists(merged_pdf_path):
                os.remove(merged_pdf_path)
    # mergePDF = EncryptionMixin.with_encryption(mergePDF)


    @action(detail=False, methods=["post"])
    def process_notes(self, request):
        file = request.FILES.get('file')

        # Create a temporary filename
        temp_filename = f'temp_{file.name}'
        with open(temp_filename, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        try:
            os.system(f"python notescan.py {temp_filename}")
        except subprocess.CalledProcessError as e:
            # Handle errors from notescan.py
            return HttpResponse(f"Error processing files: {e}", status=500)

        os.remove(temp_filename)
        file_path = os.path.join(os.getcwd(), 'page0000.png')  # Assuming it's in the current directory

    # Check if the file exists
        if os.path.exists(file_path):
            return FileResponse(open(file_path, 'rb'), as_attachment=True, filename='page0000.png')
        else:
            return HttpResponseNotFound("File not found")
    
    
    @action(detail=False, methods=["post"])
    @EncryptionMixin.simple_encrypt
    def imageCompressor(self,request):
        if request.method == "POST" and request.FILES.get("file"):
            
            image_file = request.FILES["file"]
            scale_factor = float(request.POST.get("scale_factor", 0.5))  # Default to 0.5 if not provided

            try:
                image = Image.open(image_file)
                img_format = image.format

                width, height = image.size
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)

                downsampled_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

                img_io = BytesIO()
                downsampled_image.save(img_io, format=img_format)
                img_io.seek(0)

                content_type = f"image/{img_format.lower()}"
                response = HttpResponse(img_io, content_type=content_type)
                response["Content-Disposition"] = f'attachment; filename="downsampled_image.{img_format.lower()}"'
                return response

            except Exception as e:
                return JsonResponse({"error": f"Error processing the image: {str(e)}"}, status=400)

        return JsonResponse({"error": "Invalid request"}, status=400)
    
    # @action(detail=False, methods=["post"])
    # def imageCompressor(self, request):
    #     if request.method == "POST" and request.FILES.get("file"):
    #         try:
    #             # Get password from request (you might want to send this securely)
    #             password = 'your-secret-password'
    #             if not password:
    #                 return JsonResponse({"error": "Password is required for decryption"}, status=400)
                
    #             # Get the encrypted file
    #             encrypted_file = request.FILES["file"]
    #             encrypted_data = encrypted_file.read()
                
    #             # Decrypt the file
    #             decrypted_data = self.decrypt_file(encrypted_data, password)
                
    #             # Process the image (your original compression logic)
    #             scale_factor = float(request.POST.get("scale_factor", 0.5))
    #             image = Image.open(BytesIO(decrypted_data))
    #             img_format = image.format

    #             width, height = image.size
    #             new_width = int(width * scale_factor)
    #             new_height = int(height * scale_factor)

    #             downsampled_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    #             img_io = BytesIO()
    #             downsampled_image.save(img_io, format=img_format)
    #             img_io.seek(0)
    #             processed_image_data = img_io.getvalue()
                
    #             # Re-encrypt the processed image
    #             reencrypted_data = self.encrypt_file(processed_image_data, password)
                
    #             # Send the encrypted response
    #             response = HttpResponse(reencrypted_data, content_type="application/octet-stream")
    #             response["Content-Disposition"] = f'attachment; filename="processed_encrypted_image.enc"'
    #             return response

    #         except Exception as e:
    #             return JsonResponse({"error": f"Error processing the file: {str(e)}"}, status=400)

    #     return JsonResponse({"error": "Invalid request"}, status=400)

    
    @action(detail=False, methods=["post"])
    def excel_to_pdf(self, request):
        excel_file = request.FILES.get('file')

        if not excel_file:
            messages.error(request, 'Please select an Excel file to convert.')

        try:
            df = pd.read_excel(excel_file)
            html_content = df.to_html(index=False)
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <style>
                    table {{
                        border-collapse: collapse;
                        width: 100%;
                        margin: 20px 0;
                    }}
                    th, td {{
                        border: 1px solid #ddd;
                        padding: 8px;
                        text-align: left;
                    }}
                    th {{
                        background-color: #f2f2f2;
                    }}
                    tr:nth-child(even) {{
                        background-color: #f9f9f9;
                    }}
                </style>
            </head>
            <body>   
                {html_content}
            </body>
            </html>
            """

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_html_filename = f"temp_excel_conversion_{timestamp}.html"
            temp_pdf_filename = f"excel_to_pdf_{timestamp}.pdf"

            temp_html_path = os.path.join(settings.MEDIA_ROOT, temp_html_filename)
            with open(temp_html_path, "w", encoding='utf-8') as f:
                f.write(html_content)

            options = {
                'page-size': 'A4',
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in',
                'encoding': "UTF-8",
                'no-outline': None
            }

            pdfkit.from_file(temp_html_path, os.path.join(settings.MEDIA_ROOT, temp_pdf_filename), options=options)

            with open(os.path.join(settings.MEDIA_ROOT, temp_pdf_filename), 'rb') as f:
                pdf_content = f.read()

            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{temp_pdf_filename}"'

            os.remove(temp_html_path)
            os.remove(os.path.join(settings.MEDIA_ROOT, temp_pdf_filename))  # Remove PDF after download

            messages.success(request, 'PDF generated successfully!')
            return response

        except Exception as e:
            messages.error(request, f'Error during conversion: {str(e)}')
            return HttpResponse("error here")
    
    @action(detail=False, methods=["post"])
    def compress_pdf(self, request):
        if request.method == 'POST':
            # Get the uploaded file and target size
            uploaded_file = request.FILES.get('pdf_file')
            target_size_kb = request.POST.get('target_size_kb')

            if not uploaded_file or not target_size_kb:
                return JsonResponse({"error": "Both PDF file and target size are required."}, status=400)

            try:
                target_size_kb = float(target_size_kb)
            except ValueError:
                return JsonResponse({"error": "Target size must be a number."}, status=400)

            # Define upload paths
            upload_dir = os.path.join(settings.MEDIA_ROOT, "uploads")
            compressed_dir = os.path.join(settings.MEDIA_ROOT, "compressed")

            # Ensure directories exist
            os.makedirs(upload_dir, exist_ok=True)
            os.makedirs(compressed_dir, exist_ok=True)

            # Save the uploaded file in MEDIA_ROOT/uploads/
            temp_file_path = os.path.join(upload_dir, uploaded_file.name)
            with open(temp_file_path, 'wb') as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)

            # Compress the PDF
            compressor = PDFCompressor()
            compressed_file_path = compressor.compress_to_target_size(temp_file_path, target_size_kb)

            if compressed_file_path:
                # Move compressed file to MEDIA_ROOT/compressed/
                compressed_output_path = os.path.join(compressed_dir, Path(compressed_file_path).name)
                os.rename(compressed_file_path, compressed_output_path)

                # Open the compressed file for reading
                file_handle = open(compressed_output_path, 'rb')

                # Create a custom HttpResponse with cleanup logic
                response = HttpResponse(file_handle, content_type="application/pdf")
                response["Content-Disposition"] = f'attachment; filename="{Path(compressed_output_path).name}"'

                # Define cleanup logic in the close method
                def cleanup():
                    file_handle.close()  # Close the file handle
                    try:
                        # Delete the uploaded and compressed files
                        for file_path in [temp_file_path, compressed_output_path]:
                            if os.path.exists(file_path):
                                os.remove(file_path)
                        print("Cleanup successful.")
                    except Exception as e:
                        print(f"Cleanup error: {e}")

                # Attach the cleanup logic to the response
                response.close = cleanup

                return response
            else:
                return JsonResponse({"error": "Failed to compress the PDF."}, status=500)


    # def audio_to_text(self,audio_path):
    #     recognizer = sr.Recognizer()

    #     # Convert MP3 to WAV using pydub
    #     wav_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    #     try:
    #         audio = AudioSegment.from_file(audio_path)
    #         audio.export(wav_file.name, format="wav")

    #         # Use the WAV file for speech recognition
    #         with sr.AudioFile(wav_file.name) as source:
    #             audio_data = recognizer.record(source)
    #             text = recognizer.recognize_google(audio_data)
    #             return text
    #     except sr.UnknownValueError:
    #         return "Could not understand the audio."
    #     except sr.RequestError:
    #         return "Request error. Please check your network connection."
    #     except Exception as e:
    #         return f"Error processing audio file: {str(e)}"
    #     finally:
    #         if os.path.exists(wav_file.name):
    #             pass
    #             # os.unlink(wav_file.name)  # Clean up temporary WAV file


    # def text_to_pdf(self,text):
    #     pdf = FPDF()
    #     pdf.set_auto_page_break(auto=True, margin=15)
    #     pdf.add_page()

    #     pdf.set_font("Arial", size=12)
    #     pdf.multi_cell(0, 10, text)

    #     pdf_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    #     pdf.output(pdf_file.name)
    #     return pdf_file.name

    # @action(detail=False, methods=["post"])
    # def audio_to_pdf_view(self,request):
    #     if request.method == "POST" and request.FILES.get("file"):
    #         audio_file = request.FILES["file"]

    #         # Save the uploaded audio file to a temporary location
    #         temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    #         try:
    #             for chunk in audio_file.chunks():
    #                 temp_audio.write(chunk)
    #             temp_audio.close()

    #             # Convert audio to text
    #             text = self.audio_to_text(temp_audio.name)
    #             if not text or "Error" in text:
    #                 return JsonResponse({"error": text}, status=400)

    #             # Convert text to PDF
    #             pdf_path = self.text_to_pdf(text)

    #             # Serve the PDF as a response
    #             with open(pdf_path, "rb") as pdf_file:
    #                 response = HttpResponse(pdf_file.read(), content_type="application/pdf")
    #                 response["Content-Disposition"] = f"attachment; filename=output.pdf"
    #                 return response

    #         finally:
    #             print("fine")
    #             # Clean up temporary files
    #             # if os.path.exists(temp_audio.name):
    #             #     os.unlink(temp_audio.name)
    #             # if os.path.exists(pdf_path):
    #             #     os.unlink(pdf_path)

    #     return JsonResponse({"error": "Invalid request"}, status=400)