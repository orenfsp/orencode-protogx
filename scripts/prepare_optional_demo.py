"""Create local ignored demo keys; never print secret material or modify .env."""
from pathlib import Path

from cryptography.fernet import Fernet
from jwcrypto import jwk


def main():
    root=Path(__file__).resolve().parent.parent
    directory=root/"tmp"
    directory.mkdir(exist_ok=True)
    key_file=directory/"fsp-id-demo.pem"
    if not key_file.exists():
        key_file.write_bytes(jwk.JWK.generate(kty="RSA",size=2048).export_to_pem(private_key=True,password=None))
    env_file=directory/"optional-demo.env"
    if not env_file.exists():
        env_file.write_text("\n".join(["DJANGO_DEBUG=1","DEMO_SEED_ENABLED=1","DEMO_ENVIRONMENT=local","FSP_OIDC_ENABLED=1","FSP_OIDC_ISSUER=http://127.0.0.1:8000",f"FSP_OIDC_PRIVATE_KEY_FILE={key_file.as_posix()}","FSP_DEMO_CLIENT_ID=fsp-fictional-client",f"INTEGRATION_ENCRYPTION_KEY={Fernet.generate_key().decode()}","FSP_WEBHOOK_HOSTS=127.0.0.1","FSP_WEBHOOK_ALLOW_LOOPBACK=1"])+"\n",encoding="utf-8")
    print("Local ignored demo key/config prepared in tmp/. Existing files preserved.")


if __name__=="__main__":
    main()
