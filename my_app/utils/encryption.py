from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from functools import wraps
from django.http import HttpResponse, JsonResponse
from io import BytesIO
import logging
from django.utils.datastructures import MultiValueDict
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile

logger = logging.getLogger(__name__)

class EncryptionMixin:
    @staticmethod
    def get_key(password):
        """Convert password to 32-byte key (same as standalone script)"""
        return password.encode().ljust(32, b'\0')[:32]
    
    def encrypt_data(self, data, password):
        """AES-256-CBC encryption (matches standalone script)"""
        try:
            key = self.get_key(password)
            iv = get_random_bytes(16)
            cipher = AES.new(key, AES.MODE_CBC, iv)
            return iv + cipher.encrypt(pad(data, AES.block_size))
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise

    def decrypt_data(self, encrypted_data, password):
        """AES-256-CBC decryption (matches standalone script)"""
        try:
            if len(encrypted_data) < 16:
                raise ValueError("Invalid encrypted data (too short)")
            
            key = self.get_key(password)
            iv = encrypted_data[:16]
            ciphertext = encrypted_data[16:]
            cipher = AES.new(key, AES.MODE_CBC, iv)
            return unpad(cipher.decrypt(ciphertext), AES.block_size)
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            raise

    @staticmethod
    def simple_encrypt(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            password = request.headers.get('X-Password')
            if not password:
                return JsonResponse(
                    {'error': 'X-Password header is required'}, 
                    status=400
                )

            # Decrypt incoming files
            if hasattr(request, 'FILES') and request.FILES:
                try:
                    new_files = MultiValueDict()
                    for field_name, file_list in request.FILES.lists():
                        decrypted_files = []
                        for file in file_list:
                            encrypted_data = file.read()
                            decrypted_data = self.decrypt_data(encrypted_data, password)
                            
                            # Proper file reconstruction for both types
                            if isinstance(file, InMemoryUploadedFile):
                                decrypted_file = InMemoryUploadedFile(
                                    file=BytesIO(decrypted_data),
                                    field_name=field_name,
                                    name=file.name,
                                    content_type=file.content_type,
                                    size=len(decrypted_data),
                                    charset=file.charset
                                )
                            elif isinstance(file, TemporaryUploadedFile):
                                temp_file = TemporaryUploadedFile(
                                    name=file.name,
                                    content_type=file.content_type,
                                    size=len(decrypted_data),
                                    charset=file.charset,
                                    content_type_extra=file.content_type_extra
                                )
                                temp_file.write(decrypted_data)
                                temp_file.seek(0)
                                decrypted_file = temp_file
                            else:
                                # Fallback to simple BytesIO for other cases
                                decrypted_file = BytesIO(decrypted_data)
                            
                            decrypted_files.append(decrypted_file)
                        
                        new_files.setlist(field_name, decrypted_files)
                    
                    request._files = new_files
                except Exception as e:
                    logger.error(f"File decryption failed: {str(e)}")
                    return JsonResponse(
                        {'error': f'File decryption failed: {str(e)}'},
                        status=400
                    )

            # Process view
            response = view_func(self, request, *args, **kwargs)

            # Encrypt response if it's binary data
            if isinstance(response, HttpResponse) and response.content:
                try:
                    encrypted = self.encrypt_data(response.content, password)
                    response.content = encrypted
                    response['Content-Type'] = 'application/octet-stream'
                    if 'Content-Disposition' in response:
                        filename = response['Content-Disposition'].split('filename=')[-1].strip('"')
                        response['Content-Disposition'] = f'attachment; filename="enc_{filename}"'
                except Exception as e:
                    logger.error(f"Response encryption failed: {str(e)}")
                    return JsonResponse(
                        {'error': f'Response encryption failed: {str(e)}'},
                        status=500
                    )

            return response
        return wrapper