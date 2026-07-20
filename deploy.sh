#!/bin/bash
# Script de deployment automático para Bank Extractor
# Uso: bash deploy.sh <opción>
# Opciones: standalone, integrated, gunicorn

set -e

REPO_URL="https://github.com/Francoooo22/bank-extractor.git"
INSTALL_DIR="/var/www/bank-extractor"
PYTHON_VER="python3.10"

echo "🚀 Bank Extractor - Deployment Script"
echo "======================================="

# Verificar permisos
if [[ $EUID -ne 0 ]]; then
   echo "❌ Este script requiere privilegios de sudo"
   exit 1
fi

# Función: Instalar dependencias del sistema
install_system_deps() {
    echo "📦 Instalando dependencias del sistema..."
    apt update
    apt install -y \
        $PYTHON_VER \
        python3-pip \
        python3-venv \
        python3-dev \
        git \
        curl \
        nginx
    echo "✅ Dependencias instaladas"
}

# Función: Clonar repositorio
clone_repo() {
    echo "📁 Clonando repositorio..."
    if [ -d "$INSTALL_DIR" ]; then
        cd $INSTALL_DIR
        git fetch origin
        git pull origin main
        echo "✅ Repositorio actualizado"
    else
        mkdir -p /var/www
        git clone $REPO_URL $INSTALL_DIR
        echo "✅ Repositorio clonado"
    fi
}

# Función: Crear venv e instalar deps
setup_venv() {
    echo "🔧 Configurando entorno virtual..."
    cd $INSTALL_DIR
    $PYTHON_VER -m venv venv
    source venv/bin/activate
    pip install --upgrade pip
    pip install -r requirements.txt
    echo "✅ Entorno configurado"
}

# Función: Crear .env
create_env() {
    echo "⚙️  Creando archivo .env..."
    cat > $INSTALL_DIR/.env << 'EOF'
FLASK_ENV=production
FLASK_APP=app.py
FLASK_PORT=5001
MAX_FILE_SIZE=50M
CLEANUP_HOURS=24
EOF
    echo "✅ .env creado"
}

# Función: Setup Gunicorn + Systemd
setup_gunicorn() {
    echo "🐳 Instalando Gunicorn..."
    cd $INSTALL_DIR
    source venv/bin/activate
    pip install gunicorn

    echo "📋 Creando archivo de servicio systemd..."
    cat > /etc/systemd/system/bank-extractor.service << 'EOF'
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
    --access-logfile /var/www/bank-extractor/access.log \
    --error-logfile /var/www/bank-extractor/error.log \
    app:app

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable bank-extractor
    systemctl start bank-extractor
    echo "✅ Gunicorn configurado"
}

# Función: Configurar Nginx
setup_nginx() {
    read -p "¿Cómo deseas configurar Nginx? (1=Standalone, 2=Integrado con Dashboard): " NGINX_TYPE

    if [ "$NGINX_TYPE" = "1" ]; then
        read -p "Dominio para Bank Extractor (ej: bank.ejemplo.com): " DOMAIN
        cat > /etc/nginx/sites-available/bank-extractor << EOF
server {
    listen 80;
    server_name $DOMAIN;

    client_max_body_size 50M;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF
    elif [ "$NGINX_TYPE" = "2" ]; then
        read -p "Dominio del Dashboard (ej: dashboard.ejemplo.com): " DOMAIN
        echo "⚠️  Edita /etc/nginx/sites-available/dashboard manualmente"
        echo "   Agrega este bloque location:"
        echo ""
        echo "    location /bank-extractor {"
        echo "        proxy_pass http://127.0.0.1:5001/bank-extractor;"
        echo "        proxy_set_header Host \$host;"
        echo "        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;"
        echo "    }"
    fi

    ln -sf /etc/nginx/sites-available/bank-extractor /etc/nginx/sites-enabled/
    nginx -t && systemctl reload nginx
    echo "✅ Nginx configurado"
}

# Función: Configurar SSL
setup_ssl() {
    read -p "¿Configurar SSL con Let's Encrypt? (s/n): " SSL_CHOICE
    if [ "$SSL_CHOICE" = "s" ]; then
        apt install -y certbot python3-certbot-nginx
        read -p "Dominio para SSL (ej: bank.ejemplo.com): " SSL_DOMAIN
        certbot --nginx -d $SSL_DOMAIN
        echo "✅ SSL configurado"
    fi
}

# Función: Permisos
fix_permissions() {
    echo "🔐 Configurando permisos..."
    chown -R www-data:www-data $INSTALL_DIR
    chmod -R 755 $INSTALL_DIR/uploads
    chmod -R 755 $INSTALL_DIR/outputs
    chmod -R 755 $INSTALL_DIR/uploads/bank_extractor
    chmod -R 755 $INSTALL_DIR/outputs/bank_extractor
    echo "✅ Permisos configurados"
}

# Función: Testing
test_deployment() {
    echo "🧪 Testeando deployment..."
    sleep 2
    if curl -s http://127.0.0.1:5001/ > /dev/null; then
        echo "✅ Bank Extractor está corriendo"
    else
        echo "❌ Error: Bank Extractor no responde"
        systemctl status bank-extractor
    fi
}

# MAIN
case "$1" in
    standalone)
        install_system_deps
        clone_repo
        setup_venv
        create_env
        setup_gunicorn
        setup_nginx
        setup_ssl
        fix_permissions
        test_deployment
        echo ""
        echo "✅ Deployment completado!"
        echo "📍 Acceso: https://<tu-dominio>"
        ;;
    integrated)
        echo "ℹ️  Configurando integración con Dashboard NS..."
        clone_repo
        setup_venv
        fix_permissions
        echo "✅ Bank Extractor integrado en dashboard-ns"
        echo "📍 Acceso: https://dashboard.tu-dominio/bank-extractor"
        ;;
    gunicorn)
        setup_gunicorn
        fix_permissions
        test_deployment
        echo "✅ Gunicorn + Systemd configurado"
        ;;
    *)
        echo "Uso: $0 {standalone|integrated|gunicorn}"
        echo ""
        echo "Opciones:"
        echo "  standalone  - Deployar como app independiente"
        echo "  integrated  - Integrar con dashboard-ns existente"
        echo "  gunicorn    - Solo configurar Gunicorn"
        exit 1
        ;;
esac
