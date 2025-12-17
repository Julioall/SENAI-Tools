@echo off
setlocal

:: === CONFIGURAÇÕES ===
set EXE_PATH=dist\SENAI Tools.exe
set CERT_NAME=SENAI-Tools
set PFX_PASSWORD=SENAI-Tools
set OPENSSL_PATH="C:\Program Files\OpenSSL-Win64\bin\openssl.exe"
set SIGNTOOL="C:\Program Files (x86)\Windows Kits\10\bin\10.0.26100.0\x64\signtool.exe"
set TIMESTAMP=http://timestamp.digicert.com

:: Verifica o OpenSSL
if not exist %OPENSSL_PATH% (
    echo ❌ OpenSSL não encontrado em: %OPENSSL_PATH%
    pause
    exit /b
)

:: Verifica se o executável existe
if not exist "%EXE_PATH%" (
    echo ❌ Executável "%EXE_PATH%" não encontrado!
    pause
    exit /b
)

:: Gera a chave privada
%OPENSSL_PATH% genrsa -out %CERT_NAME%.key 2048

:: Gera o certificado autoassinado
%OPENSSL_PATH% req -new -x509 -key %CERT_NAME%.key -out %CERT_NAME%.crt -days 1825 -subj "/CN=%CERT_NAME%"

:: Exporta para .pfx
%OPENSSL_PATH% pkcs12 -export -out %CERT_NAME%.pfx -inkey %CERT_NAME%.key -in %CERT_NAME%.crt -passout pass:%PFX_PASSWORD%

:: Assina o executável com signtool
%SIGNTOOL% sign ^
    /f %CERT_NAME%.pfx ^
    /p %PFX_PASSWORD% ^
    /tr %TIMESTAMP% ^
    /td sha256 ^
    /fd sha256 ^
    /v "%EXE_PATH%"

if %errorlevel% equ 0 (
    echo ✅ Executável assinado com sucesso!
) else (
    echo ❌ Falha ao assinar o executável.
)

pause
