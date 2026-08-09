import os

CERTS_DIR = "certs"
CA_CERT = "ca.crt"
CA_KEY = "ca.key"

def generate_ca():
    if os.path.exists(CA_CERT) and os.path.exists(CA_KEY):
        return
    print("[*] Generating Root CA...")
    ext_file = "ca.ext"
    with open(ext_file, "w") as f:
        f.write("basicConstraints = critical, CA:TRUE\n")
        f.write("keyUsage = critical, keyCertSign, cRLSign\n")

    os.system(f"openssl genrsa -out {CA_KEY} 2048 2>/dev/null")
    os.system(f"openssl req -x509 -new -nodes -key {CA_KEY} -sha256 -days 3650 -out {CA_CERT} -subj '/CN=Local Custom CA' 2>/dev/null")
    os.system(f"openssl x509 -in {CA_CERT} -days 3650 -sha256 -req -signkey {CA_KEY} -extfile {ext_file} -out {CA_CERT} 2>/dev/null")
    if os.path.exists(ext_file):
        os.remove(ext_file)
    print("[*] Root CA generated successfully!")

def get_site_cert(hostname):
    if not os.path.exists(CERTS_DIR):
        os.makedirs(CERTS_DIR)
        
    cert_file = os.path.join(CERTS_DIR, f"{hostname}.crt")
    key_file = os.path.join(CERTS_DIR, f"{hostname}.key")
    csr_file = os.path.join(CERTS_DIR, f"{hostname}.csr")
    ext_file = os.path.join(CERTS_DIR, f"{hostname}.ext")
    
    if os.path.exists(cert_file) and os.path.exists(key_file):
        return cert_file, key_file

    os.system(f"openssl genrsa -out {key_file} 2048 2>/dev/null")
    os.system(f"openssl req -new -key {key_file} -out {csr_file} -subj '/CN={hostname}' 2>/dev/null")
    
    with open(ext_file, "w") as f:
        f.write(f"authorityKeyIdentifier=keyid,issuer\n")
        f.write(f"basicConstraints=CA:FALSE\n")
        f.write(f"keyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment\n")
        f.write(f"subjectAltName = DNS:{hostname}\n")

    os.system(f"openssl x509 -req -in {csr_file} -CA {CA_CERT} -CAkey {CA_KEY} -CAcreateserial -out {cert_file} -days 365 -sha256 -extfile {ext_file} 2>/dev/null")
    
    for f in [csr_file, ext_file, f"{CA_CERT}.srl"]:
        if os.path.exists(f):
            os.remove(f)
            
    return cert_file, key_file
