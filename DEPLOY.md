# 🚀 Guía de Deployment - Bank Extractor

**Para servidor Linux (recomendado Ubuntu 22.04+)**

---

## 📋 Requisitos Previos

```bash
# Verificar Python 3.8+
python3 --version

# Instalar pip, venv
sudo apt update
sudo apt install python3-pip python3-venv python3-dev -y
```

---

## 🔧 Opción 1: Standalone (Recomendado para uso independiente)

### Paso 1: Clonar repositorio

```bash
cd /var/www
sudo git clone https://github.com/Francoooo22/bank-extractor.git
cd bank-extractor
sudo chown -R $USER:$USER .
```

### Paso 2: Crear entorno virtual

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Paso 3: Crear archivo de configuración

```bash
cat > .env << 'EOF'
FLASK_ENV=production
FLASK_APP=app.py
FLASK_PORT=5001
MAX_FILE_SIZE=50M
CLEANUP_HOURS=24
EOF
```

### Paso 4: Ejecutar prueba

```bash
python3 app.py
# Debería aparecer: 🚀 Servidor corriendo en http://localhost:5001
```

---

## 🎯 Opción 2: Integrado con Dashboard-NS (Recomendado)

### Paso 1: Actualizar Dashboard-NS

```bash
cd /var/www/dashboard-ns
source venv/bin/activate
pip install -r requirements.txt
```

### Paso 2: Verificar que Bank Extractor existe

```bash
# Si no está, copiar
cp -r /var/www/bank-extractor ~/Proyectos/bank\ stractor/bank_extractor
```

### Paso 3: Acceder en

```
http://tu-dominio.com/bank-extractor
```

---

## 🐳 Opción 3: Con Gunicorn + Systemd (Production)

### Paso 1: Instalar Gunicorn

```bash
cd /var/www/bank-extractor
source venv/bin/activate
pip install gunicorn
```

### Paso 2: Crear archivo de servicio

```bash
sudo tee /etc/systemd/system/bank-extractor.service > /dev/null << 'EOF'
[Unit]
Description=Bank Extractor Flask App
After=network.target

[Service]
User=www-data
WorkingDirectory=/var/www/bank-extractor
Environment="PATH=/var/www/bank-extractor/venv/bin"
ExecStart=/var/www/bank-extractor/venv/bin/gunicorn \
    --workers 4 \
    --worker-class sync \
    --bind 127.0.0.1:5001 \
    --timeout 120 \
    app:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF
```

### Paso 3: Activar servicio

```bash
sudo systemctl daemon-reload
sudo systemctl start bank-extractor
sudo systemctl enable bank-extractor
sudo systemctl status bank-extractor
```

---

## 🌐 Paso 4: Configurar Nginx (Reverse Proxy)

### Opción A: Standalone en puerto separado

```nginx
server {
    listen 80;
    server_name bank-extractor.tu-dominio.com;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Opción B: Integrado en Dashboard (path /bank-extractor)

```nginx
server {
    listen 80;
    server_name dashboard.tu-dominio.com;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /bank-extractor {
        proxy_pass http://127.0.0.1:5000/bank-extractor;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### Activar configuración

```bash
sudo nginx -t
sudo systemctl reload nginx
```

---

## 🔒 SSL con Let's Encrypt (Recomendado)

```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d bank-extractor.tu-dominio.com
# O para dashboard existing:
sudo certbot --nginx -d dashboard.tu-dominio.com
```

---

## 📊 Monitoreo

### Ver logs

```bash
# Gunicorn
sudo journalctl -u bank-extractor -f

# Aplicación
tail -f /var/www/bank-extractor/bank_extractor.log

# Nginx
tail -f /var/log/nginx/error.log
```

### Reiniciar servicio

```bash
sudo systemctl restart bank-extractor
sudo systemctl restart nginx
```

---

## 🧪 Testing en Servidor

```bash
# Verificar que está corriendo
curl http://127.0.0.1:5001/

# Desde otra máquina
curl http://bank-extractor.tu-dominio.com/
```

---

## 📈 Escala/Optimización

### Aumentar workers Gunicorn

```bash
# En /etc/systemd/system/bank-extractor.service
ExecStart=/var/www/bank-extractor/venv/bin/gunicorn \
    --workers 8 \  # Aumentar según CPU cores (2 * cores + 1)
```

### Aumentar memoria permitida

```bash
# En app.py
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
```

---

## 🆘 Troubleshooting

### "Connection refused"
```bash
sudo systemctl status bank-extractor
sudo systemctl restart bank-extractor
```

### "Permission denied" en uploads/
```bash
sudo chown -R www-data:www-data /var/www/bank-extractor/uploads
sudo chown -R www-data:www-data /var/www/bank-extractor/outputs
sudo chmod 755 /var/www/bank-extractor/uploads
sudo chmod 755 /var/www/bank-extractor/outputs
```

### "ModuleNotFoundError: No module named 'pdfplumber'"
```bash
source /var/www/bank-extractor/venv/bin/activate
pip install pdfplumber pandas openpyxl
```

### PDFs no se procesan
```bash
tail -f /var/www/bank-extractor/bank_extractor.log
# Buscar errores
```

---

## 📦 Backup & Restore

### Backup

```bash
cd /var/www
tar -czf bank-extractor-backup.tar.gz bank-extractor/
# Excluir carpetas grandes
tar --exclude='venv' --exclude='__pycache__' \
    -czf bank-extractor-backup.tar.gz bank-extractor/
```

### Restore

```bash
cd /var/www
tar -xzf bank-extractor-backup.tar.gz
cd bank-extractor
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart bank-extractor
```

---

## 🔄 Actualizar desde GitHub

```bash
cd /var/www/bank-extractor
git fetch origin
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart bank-extractor
```

---

## ✅ Checklist de Deployment

- [ ] Git clonado en /var/www/bank-extractor
- [ ] Venv creado e instaladas deps
- [ ] Archivo .env configurado
- [ ] Prueba manual: `python3 app.py` funciona
- [ ] Gunicorn instalado
- [ ] Systemd service creado y habilitado
- [ ] Nginx configurado
- [ ] SSL certificado (Let's Encrypt)
- [ ] Logs checkeados
- [ ] Permisos de carpetas correctos
- [ ] Dominio/DNS apuntando a servidor

---

## 🌐 Deploy alternativo — Render.com (gratis)

Sin dependencias de sistema (no usa Tesseract/OpenCV como `ticket-extractor`), así que corre directo sobre el runtime Python nativo de Render, sin Docker.

**Archivo:** `render.yaml` en la raíz del repo.

### Pasos

1. En [render.com](https://render.com) → **New** → **Blueprint** → conectar el repo `Francoooo22/bank-extractor`. Render detecta `render.yaml` solo (`type: web`, `runtime: python`, plan **Free**).
2. Sin Blueprint: **New** → **Web Service** → conectar el repo → Render detecta Python automáticamente. Build command: `pip install -r requirements.txt gunicorn`. Start command: `gunicorn app:app --workers 2 --timeout 120 --bind 0.0.0.0:$PORT`. Plan **Free**.
3. Deploy inicial: instala deps puras de Python (`pdfplumber`, `pandas`, `openpyxl`), sin build de imagen — mucho más rápido que `ticket-extractor`.
4. URL pública: `https://bank-extractor-<hash>.onrender.com`.

### Limitaciones del plan free

- **Sleep tras 15 min de inactividad** — cold start ~30-60s en el primer request.
- **Disco efímero** — `uploads/`/`outputs/` se borran en cada reinicio del contenedor, igual que en el server propio (ya se limpian solas a las 24h, no cambia el comportamiento esperado).
- **Sin autenticación** — este servicio no tiene login. Al quedar público en `onrender.com`, cualquiera con la URL puede subir/ver extractos bancarios. Evaluar antes de compartir la URL ampliamente.

### Nota

`requirements.txt` incluye `python-magic`, pero no se usa en ningún `.py` del repo — no requiere `libmagic` de sistema, así que no afecta el deploy nativo. Se puede sacar en una limpieza aparte si querés.

---

## 📞 Soporte

Documentación completa: [README.md](README.md)  
Issues: https://github.com/Francoooo22/bank-extractor/issues
