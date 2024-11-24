

from datetime import datetime
from io import BytesIO
import subprocess
import tempfile
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
import numpy as np
from django.utils.text import slugify
import pdfkit
# from openpyxl import Workbook
from django.contrib import messages 
from fpdf import FPDF
import speech_recognition as sr
from pydub import AudioSegment



class FileOperationsViewSet(viewsets.ViewSet):

    # @action(detail=False, methods=['get'])
    # def index(self, request):
    #     return HttpResponse("hello")
    def split_pdf(self, pdf_path, output_folder):
        with open(pdf_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            split_files = []
            for i in range(len(reader.pages)):
                writer = PyPDF2.PdfWriter()
                writer.add_page(reader.pages[i])

                # Save each page as a separate PDF
                output_filename = os.path.join(output_folder, f"page_{i + 1}.pdf")
                with open(output_filename, 'wb') as output_pdf:
                    writer.write(output_pdf)
                split_files.append(output_filename)
        return split_files
    
    @action(detail=False, methods=['post'])
    def split_pdf_file(self, request):
        """Endpoint to handle PDF splitting."""
        uploaded_file = request.FILES.get('file')

        if not uploaded_file:
            return Response({"error": "No file provided"}, status=status.HTTP_400_BAD_REQUEST)

        # Save uploaded file temporarily
        temp_pdf_path = default_storage.save(uploaded_file.name, uploaded_file)
        temp_pdf_full_path = default_storage.path(temp_pdf_path)
        print(temp_pdf_full_path)

        # Define output folder for split PDFs
        output_folder = os.path.join(settings.MEDIA_ROOT, "split_pdfs")
        os.makedirs(output_folder, exist_ok=True)

        try:
            # Split the PDF and create a zip file
            split_files = self.split_pdf(temp_pdf_full_path, output_folder)
            zip_filename = "split_pdfs.zip"
            zip_filepath = os.path.join(output_folder, zip_filename)
            with zipfile.ZipFile(zip_filepath, 'w') as zipf:
                for file in split_files:
                    zipf.write(file, os.path.basename(file))
            for file in split_files:
                os.remove(file)  # Clean up individual files after zipping

            # Return the zip file as a response
            with open(zip_filepath, 'rb') as zipf:
                response = HttpResponse(zipf.read(), content_type='application/zip')
                response['Content-Disposition'] = f'attachment; filename={zip_filename}'
                return response
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        finally:
            # Clean up the zip file
            if os.path.exists(zip_filepath):
                os.remove(zip_filepath)

    def merge_pdfs(self, pdf_files):
        # Initialize PdfMerger
        merger = PyPDF2.PdfMerger()

        # Append each uploaded PDF file
        for pdf in pdf_files:
            merger.append(pdf)

        # Create the merged PDF in memory
        output_filename = 'merged_output.pdf'
        output_path = default_storage.path(output_filename)
        with open(output_path, 'wb') as output_pdf:
            merger.write(output_pdf)

        return output_path
    
    @action(detail=False, methods=['post'])
    def mergePDF(self, request):
        if request.method == 'POST':
            pdf_files = request.FILES.getlist('files')
            if not pdf_files:
                return JsonResponse({"error": "No files provided"}, status=400)

                # Merge the PDF files
            try:
                merged_pdf_path = self.merge_pdfs(pdf_files)
            except Exception as e:
                return JsonResponse({"error": str(e)}, status=500)

                # Return the merged PDF as a downloadable response
            with open(merged_pdf_path, 'rb') as merged_pdf:
                response = HttpResponse(merged_pdf.read(), content_type='application/pdf')
                response['Content-Disposition'] = 'attachment; filename="merged_output.pdf"'
                return response


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
    
    # def lanczos_kernel(self, x, a=3):
    #     if x == 0:
    #         return 1
    #     elif abs(x) < a:
    #         return np.sinc(x) * np.sinc(x / a)
    #     else:
    #         return 0
    
    # def resample_lanczos_1d(self,data, new_size, a=3):
    #     old_size = len(data)
    #     scale = old_size / new_size
    #     resampled = np.zeros(new_size)
        
    #     for i in range(new_size):
    #         orig_x = i * scale
    #         value = 0
    #         for j in range(-a + 1, a): 
    #             neighbor_x = int(np.floor(orig_x)) + j
    #             if 0 <= neighbor_x < old_size:  
    #                 value += data[neighbor_x] * self.lanczos_kernel(orig_x - neighbor_x, a)
    #         resampled[i] = value
        
    #     return resampled

    # def lanczos_resample(self, image_array, new_width, new_height, a=3):
    #     temp = np.array([self.resample_lanczos_1d(row, new_width, a) for row in image_array])
    #     resampled_image = np.array([self.resample_lanczos_1d(temp[:, i], new_height, a) for i in range(temp.shape[1])]).T
    #     return resampled_image

    # @action(detail=False, methods=["post"])
    # def imageCompressor(self, request):
    #     input_file = request.FILES.get('file')  # Filename
    #     scale_factor = 0.5  # Default scale factor is 0.5
        
    #     if not input_file:
    #         return JsonResponse({"error": "Input file parameter is required."}, status=400)
        
    #     try:
    #         # Save uploaded file to default storage
    #         temp_file_path = default_storage.save(input_file.name, input_file)
    #         temp_file_full_path = default_storage.path(temp_file_path)
    #         print(f"Uploaded file saved at: {temp_file_full_path}")

    #         # Define output folder under MEDIA_ROOT
    #         output_folder = os.path.join(settings.MEDIA_ROOT, "resampled_images")
    #         os.makedirs(output_folder, exist_ok=True)

    #         # Output file path
    #         file_base, file_ext = os.path.splitext(input_file.name)
    #         output_file = f"{file_base}_resampled{file_ext}"
    #         output_file_path = os.path.join(output_folder, output_file)

    #         # Open the image and convert to numpy array
    #         image = Image.open(temp_file_full_path)
    #         image_array = np.array(image)

    #         # Calculate new dimensions
    #         height, width = image_array.shape[:2]
    #         new_width = int(width * scale_factor)
    #         new_height = int(height * scale_factor)

    #         # Apply Lanczos resampling
    #         if len(image_array.shape) == 3:  # RGB or RGBA image
    #             resampled_channels = [
    #                 self.lanczos_resample(image_array[..., channel], new_width, new_height)
    #                 for channel in range(image_array.shape[2])
    #             ]
    #             resampled_array = np.stack(resampled_channels, axis=-1)
    #         else:  # Grayscale image
    #             resampled_array = self.lanczos_resample(image_array, new_width, new_height)

    #         # Convert back to image and save
    #         resampled_image = Image.fromarray(np.clip(resampled_array, 0, 255).astype('uint8'))
    #         resampled_image.save(output_file_path)

    #         # Delete temporary uploaded file
    #         if default_storage.exists(temp_file_path):
    #             default_storage.delete(temp_file_path)

    #         response = FileResponse(open(output_file_path, 'rb'), as_attachment=True, filename=output_file)

    #         # Add cleanup for output file after response
    #         # def cleanup_file(file_path):
    #         #     if os.path.exists(file_path):
    #         #         os.remove(file_path)

    #         # response['cleanup_file_path'] = output_file_path  # Custom attribute for cleanup
    #         # response.close = lambda *args, **kwargs: cleanup_file(response['cleanup_file_path']) or super(FileResponse, response).close(*args, **kwargs)

    #         return response
        
    #     except Exception as e:
    #         return JsonResponse({"error": str(e)}, status=500)
    @action(detail=False, methods=["post"])
    def imageCompressor(self,request):
        if request.method == "POST" and request.FILES.get("file"):
            
            image_file = request.FILES["file"]
            scale_factor = float(request.POST.get("scale_factor", 0.5))  # Default to 0.5 if not provided

            try:
                # Open the image from the uploaded file
                image = Image.open(image_file)

                # Get the original format of the uploaded image (e.g., 'JPEG', 'PNG', etc.)
                img_format = image.format

                # Calculate new dimensions
                width, height = image.size
                new_width = int(width * scale_factor)
                new_height = int(height * scale_factor)

                # Resize the image
                downsampled_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)

                # Save the downsampled image to a BytesIO object in the original format
                img_io = BytesIO()
                downsampled_image.save(img_io, format=img_format)
                img_io.seek(0)

                # Return the image as a downloadable response with the correct content type
                content_type = f"image/{img_format.lower()}"
                response = HttpResponse(img_io, content_type=content_type)
                response["Content-Disposition"] = f'attachment; filename="downsampled_image.{img_format.lower()}"'
                return response

            except Exception as e:
                return JsonResponse({"error": f"Error processing the image: {str(e)}"}, status=400)

        return JsonResponse({"error": "Invalid request"}, status=400)

    
    @action(detail=False, methods=["post"])
    def excel_to_pdf(self, request):
        excel_file = request.FILES.get('file')

        if not excel_file:
            messages.error(request, 'Please select an Excel file to convert.')
            # return redirect('excel_to_pdf')  # Redirect back to form

        try:
            # Read Excel file
            df = pd.read_excel(excel_file)

            # Convert DataFrame to HTML with basic styling
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

            # Generate temporary filename for HTML and PDF
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_html_filename = f"temp_excel_conversion_{timestamp}.html"
            temp_pdf_filename = f"excel_to_pdf_{timestamp}.pdf"

            # Create temporary HTML file in media directory (configurable)
            temp_html_path = os.path.join(settings.MEDIA_ROOT, temp_html_filename)
            with open(temp_html_path, "w", encoding='utf-8') as f:
                f.write(html_content)

            # Configure PDF options (optional)
            options = {
                'page-size': 'A4',
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in',
                'encoding': "UTF-8",
                'no-outline': None
            }

            # Generate PDF using wkhtmltopdf (ensure it's installed and configured)
            pdfkit.from_file(temp_html_path, os.path.join(settings.MEDIA_ROOT, temp_pdf_filename), options=options)

            # Serve the generated PDF as a download response
            with open(os.path.join(settings.MEDIA_ROOT, temp_pdf_filename), 'rb') as f:
                pdf_content = f.read()

            response = HttpResponse(pdf_content, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{temp_pdf_filename}"'

            # Clean up temporary files
            os.remove(temp_html_path)
            os.remove(os.path.join(settings.MEDIA_ROOT, temp_pdf_filename))  # Remove PDF after download

            messages.success(request, 'PDF generated successfully!')
            return response

        except Exception as e:
            messages.error(request, f'Error during conversion: {str(e)}')
            return HttpResponse("error here")
    
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