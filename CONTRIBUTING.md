# Guía para Contribuidores

## 🎯 Cómo Contribuir

¡Bienvenido! Aquí te explicamos cómo contribuir al proyecto.

### Reportar Bugs

Abre un [Issue](https://github.com/Francoooo22/bank-extractor/issues) con:
- **Título claro** (ej: "Galicia: No detecta números negativos")
- **Pasos para reproducir**
- **PDF de prueba** (anónimo, si es posible)
- **Log de error** (click "Ver texto crudo" en la app)
- **Sistema operativo y versión Python**

### Sugerir Mejoras

Abre un [Issue](https://github.com/Francoooo22/bank-extractor/issues) con tag `enhancement`:
- ¿Qué funcionalidad quieres?
- ¿Por qué la necesitas?
- ¿Cómo debería verse?

### Enviar Pull Requests

#### 1. Fork y Clonar
```bash
git clone https://github.com/TU_USUARIO/bank-extractor.git
cd bank-extractor
```

#### 2. Crear rama feature
```bash
git checkout -b feature/mi-mejora
# o
git checkout -b bugfix/error-que-arreglo
```

#### 3. Hacer cambios
- Edita `extractor.py`, `app.py`, etc.
- Prueba manualmente en tu sistema
- Respeta el estilo de código existente

#### 4. Commit y Push
```bash
git add .
git commit -m "feat: agregar soporte para Banco ABC"
git push origin feature/mi-mejora
```

#### 5. Abrir PR
- Ve a GitHub
- Click "New Pull Request"
- Describe qué cambios hiciste y por qué

#### 6. Esperar review
- Responde feedback
- Actualiza tu rama si hay sugerencias

---

## 📝 Estilo de Código

### Python
- **PEP 8**: Indentación 4 espacios, `snake_case` para funciones
- **Docstrings**: En docstrings con triple comillas, describe parámetros y return
- **Comentarios**: Solo para lógica no obvia
- **Sin type hints**: Por compatibilidad con Python 3.8

### Commits
```
feat:   Nueva funcionalidad (agregar soporte Banco X)
fix:    Corrección de bug
refactor: Cambios sin alterar comportamiento
docs:   Actualizaciones de documentación
test:   Tests nuevos o actualizados
```

---

## 🧪 Testing

### Pruebas Manuales
1. Descarga PDFs de diferentes bancos
2. Sube a la app
3. Verifica que se extraigan correctamente los movimientos
4. Descarga Excel y valida formato

### Agregar Soporte para Nuevo Banco

1. **Obtén un PDF de ejemplo** (de preferencia anónimo)
2. **Edita `extractor.py`:**
   - Agrega entrada en `PATRONES`
   - Agrega keywords en `detectar_banco()`
3. **Prueba:**
   ```python
   from extractor import extraer_movimientos
   resultado = extraer_movimientos('path/to/pdf.pdf', 'tu_banco')
   for mov in resultado['movimientos']:
       print(mov)
   ```
4. **Commit y PR**

---

## 🔍 Antes de Hacer Push

- [ ] Código sigue PEP 8
- [ ] Funcionalidad nueva tiene docstring
- [ ] Probaste en tu sistema (Windows/Mac/Linux)
- [ ] No agregaste `__pycache__` ni `.env`
- [ ] Commit message es claro
- [ ] No hay archivos sensibles (PDFs reales, credenciales)

---

## 📚 Estructura de Directorios

```
bank-extractor/
├── app.py              ← Rutas Flask
├── extractor.py        ← Motor de extracción (la mayoría de lógica)
├── lanzar.py           ← Launcher automático
├── requirements.txt    ← Dependencias
├── README.md           ← User-facing docs
├── ARCHITECTURE.md     ← Este proyecto (técnico)
├── CONTRIBUTING.md     ← Tú estás aquí
├── templates/
│   └── index.html      ← UI interactiva
├── uploads/            ← PDFs subidos (tmp, no commit)
└── outputs/            ← Excels generados (tmp, no commit)
```

---

## ✨ Ejemplos de Contribuciones Bienvenidas

- ✅ Agregar soporte para nuevo banco argentino
- ✅ Mejorar manejo de fechas (años de 2 dígitos, etc)
- ✅ Mejor UI/UX (CSS, drag & drop mejorado, etc)
- ✅ Documentación en español (¡mantengamos Spanish-first!)
- ✅ Performance improvements
- ✅ Tests automatizados

---

## 🚫 Lo que NO hacemos

- ❌ Integración con APIs de bancos (requeriría credenciales)
- ❌ Descarga automática de PDFs (solo extrae lo que sube el usuario)
- ❌ Almacenamiento en cloud (local-only por privacidad)

---

## 📞 Preguntas?

- Abre un [Discussion](https://github.com/Francoooo22/bank-extractor/discussions)
- O escribe un Issue con tag `question`

¡Gracias por contribuir! 🙏
