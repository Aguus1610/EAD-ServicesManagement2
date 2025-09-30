# 🚀 Guía Completa de Despliegue en Render

Esta guía te llevará paso a paso para desplegar **EAD Oleohidráulica Services Management System** en Render.

## 📋 Prerrequisitos

- ✅ Cuenta en [Render](https://render.com)
- ✅ Repositorio en GitHub: `https://github.com/Aguus1610/EAD-ServicesManagement2`
- ✅ Código ya subido al repositorio

## 🎯 Método 1: Despliegue Automático con render.yaml

### Paso 1: Crear Servicio en Render

1. **Ir a Render Dashboard**
   - Visita: https://dashboard.render.com
   - Inicia sesión con tu cuenta

2. **Crear Nuevo Servicio**
   - Click en **"New +"**
   - Selecciona **"Blueprint"**

3. **Conectar Repositorio**
   - Selecciona **"Connect a repository"**
   - Busca y selecciona: `Aguus1610/EAD-ServicesManagement2`
   - Click **"Connect"**

4. **Configurar Blueprint**
   - Render detectará automáticamente el archivo `render.yaml`
   - Revisa la configuración:
     - **Service Name**: `ead-oleohidraulica`
     - **Region**: `oregon` (o tu región preferida)
     - **Plan**: `starter` (o el plan que prefieras)

5. **Desplegar**
   - Click **"Apply"**
   - Render comenzará el despliegue automáticamente

### Paso 2: Configurar Variables de Entorno (Automáticas)

Las siguientes variables se configuran automáticamente desde `render.yaml`:

```yaml
SECRET_KEY: [Generada automáticamente]
FLASK_ENV: production
DATABASE_PATH: /opt/render/project/src/equipos.db
UPLOAD_FOLDER: /tmp/uploads
CACHE_TYPE: simple
CACHE_DEFAULT_TIMEOUT: 300
MAX_CONTENT_LENGTH: 16777216
```

## 🎯 Método 2: Despliegue Manual

### Paso 1: Crear Web Service

1. **Nuevo Web Service**
   - En Render Dashboard, click **"New +"**
   - Selecciona **"Web Service"**

2. **Conectar Repositorio**
   - Selecciona tu repositorio: `EAD-ServicesManagement2`
   - Click **"Connect"**

### Paso 2: Configuración del Servicio

```
Name: ead-oleohidraulica
Region: Oregon (US West)
Branch: main
Runtime: Python 3
Build Command: pip install --upgrade pip && pip install -r requirements.txt && python render_init.py
Start Command: gunicorn app_web:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
```

### Paso 3: Variables de Entorno Manuales

En la sección **Environment**, agregar:

| Variable | Valor |
|----------|-------|
| `PYTHON_VERSION` | `3.11.0` |
| `FLASK_ENV` | `production` |
| `SECRET_KEY` | `[Generar clave aleatoria]` |
| `DATABASE_PATH` | `/opt/render/project/src/equipos.db` |
| `UPLOAD_FOLDER` | `/tmp/uploads` |
| `CACHE_TYPE` | `simple` |
| `CACHE_DEFAULT_TIMEOUT` | `300` |
| `MAX_CONTENT_LENGTH` | `16777216` |

### Paso 4: Configuración Avanzada

```
Plan: Starter ($7/mes) o Free (con limitaciones)
Auto-Deploy: Yes
Health Check Path: /
```

## 🔧 Configuraciones Específicas de Render

### Gunicorn Optimizado

El comando de inicio está optimizado para Render:

```bash
gunicorn app_web:app \
  --bind 0.0.0.0:$PORT \
  --workers 2 \
  --timeout 120 \
  --keep-alive 2 \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  --log-level info
```

### Persistencia de Datos

⚠️ **IMPORTANTE**: Render usa almacenamiento efímero. Para datos persistentes:

#### Opción 1: Base de Datos Externa (Recomendado)
```yaml
# Agregar a render.yaml
- type: pserv
  name: ead-database
  runtime: postgresql
  plan: starter
```

#### Opción 2: Almacenamiento en Disco Persistente
```yaml
# Agregar a render.yaml
disk:
  name: ead-data
  mountPath: /opt/render/project/data
  sizeGB: 1
```

### Configuración de Uploads

Los archivos subidos se almacenan en `/tmp/uploads` (temporal). Para persistencia:

1. **Usar servicio de almacenamiento externo** (AWS S3, Cloudinary)
2. **Configurar disco persistente** (ver arriba)

## 🌐 URLs y Dominios

### URL Automática
Render asignará una URL automática:
```
https://ead-oleohidraulica.onrender.com
```

### Dominio Personalizado
1. En el dashboard del servicio
2. Ir a **"Settings"** → **"Custom Domains"**
3. Agregar tu dominio personalizado
4. Configurar DNS según las instrucciones

## 📊 Monitoreo y Logs

### Ver Logs en Tiempo Real
```bash
# En el dashboard de Render
Logs → View Live Logs
```

### Métricas Disponibles
- CPU Usage
- Memory Usage
- Response Times
- Request Volume
- Error Rates

## 🔒 Seguridad en Producción

### Variables de Entorno Seguras
```env
SECRET_KEY=[Clave fuerte generada]
FLASK_ENV=production
DATABASE_URL=[Si usas PostgreSQL]
```

### Headers de Seguridad
La aplicación incluye configuración de seguridad:
- `SESSION_COOKIE_SECURE=True`
- `SESSION_COOKIE_HTTPONLY=True`
- `SESSION_COOKIE_SAMESITE=Lax`

## 🚨 Troubleshooting

### Error: "Application failed to start"
```bash
# Verificar logs
1. Ir a Render Dashboard
2. Seleccionar tu servicio
3. Ver "Logs" para detalles del error
```

### Error: "Module not found"
```bash
# Verificar requirements.txt
pip freeze > requirements.txt
git add requirements.txt
git commit -m "Update requirements"
git push
```

### Error: "Database not found"
```bash
# El script render_init.py debería crear la DB
# Si falla, verificar logs y variables de entorno
```

### Error: "Permission denied"
```bash
# Verificar rutas de archivos
DATABASE_PATH=/opt/render/project/src/equipos.db
UPLOAD_FOLDER=/tmp/uploads
```

## 🔄 Actualizaciones Automáticas

Con `autoDeploy: true`, cada push a la rama `main` desplegará automáticamente:

```bash
git add .
git commit -m "Update application"
git push origin main
# Render desplegará automáticamente
```

## 💰 Costos Estimados

### Plan Free
- ✅ Gratis
- ⚠️ Limitaciones: 750 horas/mes, se duerme tras inactividad
- ⚠️ No persistencia de archivos

### Plan Starter ($7/mes)
- ✅ Sin límite de horas
- ✅ No se duerme
- ✅ SSL automático
- ✅ Dominios personalizados

### Plan Standard ($25/mes)
- ✅ Más recursos
- ✅ Mejor rendimiento
- ✅ Soporte prioritario

## 📞 Soporte

### Documentación Oficial
- [Render Docs](https://render.com/docs)
- [Python en Render](https://render.com/docs/deploy-flask)

### Comunidad
- [Render Community](https://community.render.com)
- [Discord de Render](https://discord.gg/render)

## ✅ Checklist de Despliegue

- [ ] Repositorio conectado a Render
- [ ] Variables de entorno configuradas
- [ ] Build command configurado
- [ ] Start command configurado
- [ ] Health check funcionando
- [ ] Logs sin errores
- [ ] Aplicación accesible via URL
- [ ] Funcionalidades principales probadas
- [ ] Base de datos inicializada
- [ ] Uploads funcionando (temporal)

## 🎉 ¡Listo!

Tu aplicación **EAD Oleohidráulica** estará disponible en:
```
https://ead-oleohidraulica.onrender.com
```

### Funcionalidades Disponibles:
- ✅ Dashboard con widget de tiempo real
- ✅ Gestión de equipos y trabajos
- ✅ Importación de Excel
- ✅ Gestión de clientes
- ✅ Interfaz responsive
- ✅ APIs de cotización del dólar

---

**¿Problemas?** Revisa los logs en Render Dashboard o contacta al desarrollador.
