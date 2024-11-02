

from io import BytesIO
from django.http import HttpResponse, JsonResponse
# import numpy as np
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework import status
# import cv2
import os
import zipfile
from django.conf import settings
from django.core.files.storage import default_storage
from rest_framework import viewsets, status
import PyPDF2
# from PIL import Image
# import rembg
# from rembg import remove


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
    
    # @action(detail=False, methods=['post'])
    # def detect_face(self, request):
    #     images = request.FILES.getlist('images')
    #     processed_images = []

    #     # Load the pre-trained face detection model
    #     face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
    #     face_cascade = cv2.CascadeClassifier(face_cascade_path)

    #     for image_file in images:
    #         # Load image with PIL for processing
    #         input_image = Image.open(image_file)

    #         # Convert to OpenCV format for face detection
    #         img_cv = cv2.cvtColor(np.array(input_image), cv2.COLOR_RGB2BGR)
    #         gray = cv2.cvtColor(img_cv, cv2.COLOR_BGR2GRAY)

    #         # Detect faces
    #         faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))

    #         if len(faces) > 0:
    #             # Convert the PIL image to bytes for rembg
    #             input_buffer = BytesIO()
    #             input_image.save(input_buffer, format="PNG")
    #             input_bytes = input_buffer.getvalue()

    #             # Remove background using rembg and read back as a PIL image
    #             output_image_bytes = remove(input_bytes)
    #             output_image = Image.open(BytesIO(output_image_bytes)).convert("RGBA")

    #             # Add a white background
    #             white_bg = Image.new("RGBA", output_image.size, "WHITE")
    #             output_image = Image.alpha_composite(white_bg, output_image).convert("RGB")
    #         else:
    #             # Keep the original image if no face is detected
    #             output_image = input_image.convert("RGB")
            
    #         output_buffer = BytesIO()
    #         output_image.save(output_buffer, format="JPEG", quality=85)
    #         output_buffer.seek(0)
    #         processed_images.append((f"processed_{image_file.name}", output_buffer))

    #     if len(processed_images) == 1:
    #         # Return single image as a downloadable file
    #         filename, image_buffer = processed_images[0]
    #         response = HttpResponse(image_buffer, content_type="image/jpeg")
    #         response['Content-Disposition'] = f'attachment; filename="{filename}"'
    #         return response
    #     else:
    #             # Create a ZIP file if multiple images
    #         zip_buffer = BytesIO()
    #         with zipfile.ZipFile(zip_buffer, "w") as zip_file:
    #             for filename, image_buffer in processed_images:
    #                 zip_file.writestr(filename, image_buffer.getvalue())
    #         zip_buffer.seek(0)
    #         response = HttpResponse(zip_buffer, content_type="application/zip")
    #         response['Content-Disposition'] = 'attachment; filename="processed_images.zip"'
    #     return HttpResponse('gubgou')
