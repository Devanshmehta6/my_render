from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from functools import wraps
from django.http import JsonResponse
from django.core.files.uploadedfile import InMemoryUploadedFile, TemporaryUploadedFile
from io import BytesIO


class EncryptionMixin:
    @staticmethod
    def get_key(password):
        """Convert password to 32-byte key"""
        return password.encode().ljust(32, b'\0')[:32]
    
    def encrypt_data(self, data, password):
        key = self.get_key(password)
        iv = get_random_bytes(16)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        encrypted = cipher.encrypt(pad(data, AES.block_size))
        return iv + encrypted  # IV + ciphertext
    
    def decrypt_data(self, encrypted_data, password):
        key = self.get_key(password)
        iv = encrypted_data[:16]
        ciphertext = encrypted_data[16:]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        return unpad(cipher.decrypt(ciphertext), AES.block_size)

    def simple_encrypt(view_func):
        @wraps(view_func)
        def wrapper(self, request, *args, **kwargs):
            password = request.headers.get('X-Password', 'defaultpass')
            
            if hasattr(request, 'FILES') and request.FILES:
                decrypted_files = {}
                for name, file in request.FILES.items():
                    try:
                        encrypted_data = file.read()
                        decrypted_data = self.decrypt_data(encrypted_data, password)
                        
                        # Handle both file types
                        if isinstance(file, InMemoryUploadedFile):
                            decrypted_file = InMemoryUploadedFile(
                                file=BytesIO(decrypted_data),
                                field_name=name,  # Use the parameter name as field_name
                                name=file.name,
                                content_type=file.content_type,
                                size=len(decrypted_data),
                                charset=file.charset
                            )
                        elif isinstance(file, TemporaryUploadedFile):
                            # For temporary files, write to a new temp file
                            temp_file = TemporaryUploadedFile(
                                name=file.name,
                                content_type=file.content_type,
                                size=len(decrypted_data),
                                charset=file.charset
                            )
                            temp_file.write(decrypted_data)
                            temp_file.seek(0)
                            decrypted_file = temp_file
                        else:
                            raise ValueError(f"Unknown file type: {type(file)}")
                            
                        decrypted_files[name] = decrypted_file
                        
                    except Exception as e:
                        return JsonResponse(
                            {'error': f'Decryption failed: {str(e)}'},
                            status=400
                        )
                request._files = decrypted_files
            
            # Process view
            response = view_func(self, request, *args, **kwargs)
            
            # Encrypt response
            if hasattr(response, 'content') and isinstance(response.content, bytes):
                try:
                    encrypted = self.encrypt_data(response.content, password)
                    response.content = encrypted
                    response['Content-Type'] = 'application/octet-stream'
                    if 'Content-Disposition' in response:
                        filename = response['Content-Disposition'].split('filename=')[-1]
                        response['Content-Disposition'] = f'attachment; filename="enc_{filename}'
                except Exception as e:
                    return JsonResponse(
                        {'error': f'Response encryption failed: {str(e)}'},
                        status=500
                    )
            
            return response
        return wrapper