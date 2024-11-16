

from io import BytesIO
import shutil
import subprocess
import tempfile
from django.http import FileResponse, HttpResponse, HttpResponseNotFound, JsonResponse
# import numpy as np
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework import status
# import cv2
from django.core.files.storage import FileSystemStorage
from django.core.files.base import ContentFile
import os
import zipfile
from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import viewsets, status
import PyPDF2
# from PIL import Image
# import rembg
# from rembg import remove
# from . import notescan
# from notescan import notescan_main, get_argument_parser



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
        
        


    
    