

import subprocess
import tempfile
from django.http import FileResponse, HttpResponse, HttpResponseNotFound, JsonResponse
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

import cv2
from rembg import remove
from PIL import Image, ImageOps


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
    
    @action(detail=False, methods=['post'])
    def detectFace(self, request):
        try:
            # Get the uploaded file
            uploaded_file = request.FILES.get('image')
            if not uploaded_file:
                return JsonResponse({'error': 'No image file provided.'}, status=400)

            with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_input:
                temp_input.write(uploaded_file.read())
                temp_input_path = temp_input.name
                
            img = cv2.imread(temp_input_path)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

            # Load the pre-trained face detection model
            face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            face_cascade = cv2.CascadeClassifier(face_cascade_path)

            # Detect faces in the image
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

            if len(faces) > 0:
                # Face detected, remove background
                input_image = Image.open(temp_input_path)
                output_image = remove(input_image)
                output_image = output_image.convert("RGBA")  # Ensure alpha channel
                white_bg = Image.new("RGBA", output_image.size, "WHITE")
                output_image = Image.alpha_composite(white_bg, output_image).convert("RGB")
            else:
                # No face detected, keep the original image
                output_image = Image.open(temp_input_path).convert("RGB")

            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_output:
                temp_output_path = temp_output.name
                output_image.save(temp_output_path, "JPEG", quality=85)

            # Prepare the response with the processed image
            with open(temp_output_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type="image/jpeg")
                response['Content-Disposition'] = 'inline; filename="processed_image.jpg"'

            # Clean up temporary files
            os.remove(temp_input_path)
            os.remove(temp_output_path)

            return response

        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
