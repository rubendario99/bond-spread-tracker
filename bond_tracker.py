#!/usr/bin/env python3
"""
High Yield Bond Spread Tracker
Monitorea el spread de bonos basura desde FRED API y envía alertas a Telegram
"""

import os
import json
import requests
from datetime import datetime, timedelta

# ===== CONFIGURACIÓN =====
FRED_API_KEY = os.environ.get('FRED_API_KEY')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')

# Serie de FRED: ICE BofA US High Yield Index Option-Adjusted Spread
FRED_SERIES_ID = 'BAMLH0A0HYM2'

# Umbrales de alerta (AJUSTADOS PARA MAYOR SENSIBILIDAD)
UMBRAL_CAMBIO_DIARIO = 0.12  # Alerta si cambia más de 0.12% en un día (antes: 0.15)
UMBRAL_SPREAD_ALTO = 4.5      # Alerta si supera 4.5% (antes: 5.0)
UMBRAL_SPREAD_CRITICO = 6.0   # Alerta crítica si supera 6.0% (antes: 6.5)

# Archivo para guardar estado
STATE_FILE = 'bond_spread_state.json'


def obtener_datos_fred(dias=5):
    """
    Obtiene datos del spread de FRED API con reintentos
    Solicita últimos 'dias' días para tener histórico reciente
    """
    max_intentos = 3
    
    for intento in range(max_intentos):
        try:
            url = f'https://api.stlouisfed.org/fred/series/observations'
            params = {
                'series_id': FRED_SERIES_ID,
                'api_key': FRED_API_KEY,
                'file_type': 'json',
                'sort_order': 'desc',
                'limit': dias
            }
            
            response = requests.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if 'observations' not in data or len(data['observations']) == 0:
                raise Exception("No se recibieron datos de FRED")
            
            # Convertir y ordenar por fecha (más reciente primero)
            observaciones = []
            for obs in data['observations']:
                if obs['value'] != '.':  # Filtrar valores no disponibles
                    observaciones.append({
                        'fecha': obs['date'],
                        'valor': float(obs['value'])
                    })
            
            # Validar que los datos tengan sentido
            if len(observaciones) == 0:
                raise Exception("Todos los valores son inválidos")
            
            # Verificar que el último valor esté en rango razonable (0.5% - 30%)
            ultimo_valor = observaciones[0]['valor']
            if not (0.5 <= ultimo_valor <= 30.0):
                raise Exception(f"Valor fuera de rango razonable: {ultimo_valor}%")
            
            print(f"✅ Datos obtenidos correctamente (intento {intento + 1}/{max_intentos})")
            return observaciones
        
        except requests.exceptions.RequestException as e:
            print(f"⚠️ Intento {intento + 1}/{max_intentos} falló: {e}")
            if intento < max_intentos - 1:
                import time
                time.sleep(2)  # Esperar 2 segundos antes de reintentar
            else:
                raise Exception(f"Error al obtener datos de FRED después de {max_intentos} intentos: {e}")


def cargar_estado():
    """Carga el estado anterior desde archivo"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except:
            pass
    return None


def guardar_estado(estado):
    """Guarda el estado actual en archivo"""
    with open(STATE_FILE, 'w') as f:
        json.dump(estado, f, indent=2)


def enviar_telegram(mensaje, es_critico=False):
    """Envía mensaje a Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ Telegram no configurado")
        return False
    
    url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
    
    # Añadir emoji de alerta si es crítico
    if es_critico:
        mensaje = f"🚨🚨🚨\n{mensaje}"
    
    payload = {
        'chat_id': TELEGRAM_CHAT_ID,
        'text': mensaje,
        'parse_mode': 'HTML',
        'disable_web_page_preview': True
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        print("✅ Mensaje enviado a Telegram")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ Error enviando a Telegram: {e}")
        return False


def analizar_datos(datos_actuales, estado_anterior):
    """
    Analiza los datos y genera alertas si es necesario
    Returns: (tiene_alertas, mensaje, es_critico)
    """
    if not datos_actuales:
        return False, None, False
    
    actual = datos_actuales[0]
    fecha_actual = actual['fecha']
    spread_actual = actual['valor']
    
    alertas = []
    es_critico = False
    
    # Si no hay estado anterior, solo reportar valor actual
    if not estado_anterior:
        mensaje = (
            f"📊 <b>Inicio de Monitoreo - Bond Spread</b>\n\n"
            f"📅 Fecha: {fecha_actual}\n"
            f"📈 Spread actual: <b>{spread_actual:.2f}%</b>\n\n"
            f"🔗 <a href='https://fred.stlouisfed.org/series/BAMLH0A0HYM2'>Ver en FRED</a>"
        )
        return True, mensaje, False
    
    spread_anterior = estado_anterior['valor']
    fecha_anterior = estado_anterior['fecha']
    
    # Calcular cambio
    cambio = spread_actual - spread_anterior
    cambio_porcentual = (cambio / spread_anterior) * 100 if spread_anterior != 0 else 0
    
    # ===== ANÁLISIS DE ALERTAS =====
    
    # 1. Cambio brusco diario
    if abs(cambio) >= UMBRAL_CAMBIO_DIARIO:
        direccion = "📈 <b>SUBIDA BRUSCA</b>" if cambio > 0 else "📉 <b>BAJADA BRUSCA</b>"
        alertas.append(
            f"{direccion}\n"
            f"   Cambio: {'+' if cambio > 0 else ''}{cambio:.2f}% "
            f"({'+' if cambio_porcentual > 0 else ''}{cambio_porcentual:.1f}%)"
        )
    
    # 2. Nivel crítico
    if spread_actual >= UMBRAL_SPREAD_CRITICO:
        alertas.append(
            f"🚨 <b>NIVEL CRÍTICO</b>\n"
            f"   Spread en {spread_actual:.2f}% (umbral: {UMBRAL_SPREAD_CRITICO}%)"
        )
        es_critico = True
    elif spread_actual >= UMBRAL_SPREAD_ALTO:
        alertas.append(
            f"⚠️ <b>NIVEL ALTO</b>\n"
            f"   Spread en {spread_actual:.2f}% (umbral: {UMBRAL_SPREAD_ALTO}%)"
        )
    
    # 3. Cruce de umbrales importantes
    if spread_anterior < UMBRAL_SPREAD_ALTO and spread_actual >= UMBRAL_SPREAD_ALTO:
        alertas.append(f"⬆️ Spread cruzó umbral de <b>{UMBRAL_SPREAD_ALTO}%</b>")
    
    if spread_anterior >= UMBRAL_SPREAD_ALTO and spread_actual < UMBRAL_SPREAD_ALTO:
        alertas.append(f"⬇️ Spread cayó por debajo de <b>{UMBRAL_SPREAD_ALTO}%</b>")
    
    if spread_anterior < UMBRAL_SPREAD_CRITICO and spread_actual >= UMBRAL_SPREAD_CRITICO:
        alertas.append(f"🚨 Spread cruzó umbral CRÍTICO de <b>{UMBRAL_SPREAD_CRITICO}%</b>")
        es_critico = True
    
    # 4. Tendencia sostenida (si hay suficientes datos)
    if len(datos_actuales) >= 5:
        ultimos_5 = [d['valor'] for d in datos_actuales[:5]]
        
        # Tendencia alcista fuerte (5 días subiendo)
        if all(ultimos_5[i] > ultimos_5[i+1] for i in range(4)):
            cambio_total = ultimos_5[0] - ultimos_5[4]
            alertas.append(
                f"📈 <b>TENDENCIA ALCISTA SOSTENIDA</b>\n"
                f"   5 días consecutivos subiendo (+{cambio_total:.2f}%)"
            )
            if ultimos_5[0] > UMBRAL_SPREAD_ALTO:
                es_critico = True
        
        # Tendencia bajista fuerte (5 días bajando)
        elif all(ultimos_5[i] < ultimos_5[i+1] for i in range(4)):
            cambio_total = ultimos_5[4] - ultimos_5[0]
            alertas.append(
                f"📉 <b>TENDENCIA BAJISTA SOSTENIDA</b>\n"
                f"   5 días consecutivos bajando (-{cambio_total:.2f}%)"
            )
        
        # Tendencia alcista moderada (4 de 5 días subiendo)
        elif sum(1 for i in range(4) if ultimos_5[i] > ultimos_5[i+1]) >= 3:
            alertas.append(
                f"📈 <b>TENDENCIA ALCISTA</b>\n"
                f"   Subiendo en 4 de los últimos 5 días"
            )
    
    # ===== CONSTRUIR MENSAJE =====
    if alertas:
        emoji_tendencia = "🔺" if cambio > 0 else "🔻"
        
        mensaje = (
            f"📊 <b>ALERTA - High Yield Bond Spread</b>\n\n"
            f"📅 Fecha: {fecha_actual}\n"
            f"📈 Spread actual: <b>{spread_actual:.2f}%</b>\n"
            f"📉 Spread anterior: {spread_anterior:.2f}% ({fecha_anterior})\n"
            f"{emoji_tendencia} Cambio: {'+' if cambio > 0 else ''}{cambio:.2f}% "
            f"({'+' if cambio_porcentual > 0 else ''}{cambio_porcentual:.1f}%)\n\n"
        )
        
        mensaje += "🚨 <b>ALERTAS:</b>\n"
        for alerta in alertas:
            mensaje += f"\n• {alerta}\n"
        
        mensaje += (
            f"\n📊 Contexto histórico:\n"
            f"   • Normal: 3-5%\n"
            f"   • Crisis 2008: >20%\n"
            f"   • COVID-19: ~10%\n\n"
            f"🔗 <a href='https://fred.stlouisfed.org/series/BAMLH0A0HYM2'>Ver gráfico en FRED</a>\n"
            f"📈 <a href='https://www.tradingview.com/symbols/FRED-BAMLH0A0HYM2/'>Ver en TradingView</a>"
        )
        
        return True, mensaje, es_critico
    
    return False, None, False


def verificar_salud_sistema():
    """Verifica que el sistema esté funcionando correctamente"""
    problemas = []
    
    # Verificar variables de entorno
    if not FRED_API_KEY:
        problemas.append("❌ FRED_API_KEY no configurado")
    if not TELEGRAM_BOT_TOKEN:
        problemas.append("❌ TELEGRAM_BOT_TOKEN no configurado")
    if not TELEGRAM_CHAT_ID:
        problemas.append("❌ TELEGRAM_CHAT_ID no configurado")
    
    # Verificar última ejecución
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                estado = json.load(f)
                if 'ultima_ejecucion' in estado:
                    from datetime import datetime, timedelta
                    ultima = datetime.fromisoformat(estado['ultima_ejecucion'])
                    ahora = datetime.now()
                    dias_sin_ejecutar = (ahora - ultima).days
                    
                    if dias_sin_ejecutar > 7:
                        problemas.append(f"⚠️ No se ha ejecutado en {dias_sin_ejecutar} días")
        except:
            pass
    
    if problemas:
        mensaje = (
            f"🔧 <b>Auto-diagnóstico del Bot</b>\n\n"
            f"⚠️ Se detectaron problemas:\n\n"
        )
        for problema in problemas:
            mensaje += f"• {problema}\n"
        mensaje += f"\n<i>Por favor, revisa la configuración</i>"
        enviar_telegram(mensaje, True)
        
    return len(problemas) == 0


def enviar_heartbeat_semanal():
    """Envía un mensaje semanal confirmando que el bot funciona"""
    try:
        from datetime import datetime
        hoy = datetime.now()
        
        # Enviar heartbeat solo los viernes
        if hoy.weekday() == 4:  # 4 = Viernes
            datos = obtener_datos_fred(dias=5)
            if datos:
                spread_actual = datos[0]['valor']
                fecha_actual = datos[0]['fecha']
                
                # Calcular promedio de la semana
                spreads_semana = [d['valor'] for d in datos[:5]]
                promedio = sum(spreads_semana) / len(spreads_semana)
                
                mensaje = (
                    f"💚 <b>Heartbeat Semanal - Bot Activo</b>\n\n"
                    f"✅ El bot está funcionando correctamente\n\n"
                    f"📅 Semana terminada: {fecha_actual}\n"
                    f"📈 Spread actual: <b>{spread_actual:.2f}%</b>\n"
                    f"📊 Promedio semanal: {promedio:.2f}%\n"
                    f"📉 Rango: {min(spreads_semana):.2f}% - {max(spreads_semana):.2f}%\n\n"
                    f"{'🟢 Estado: Normal (sin alertas esta semana)' if spread_actual < 5.0 else '🟡 Estado: Vigilancia'}\n\n"
                    f"<i>Recibirás este mensaje cada viernes para confirmar que el bot funciona</i>"
                )
                
                enviar_telegram(mensaje, False)
                print("✅ Heartbeat semanal enviado")
    except Exception as e:
        print(f"⚠️ Error en heartbeat: {e}")


def main():
    """Función principal"""
    print("=" * 60)
    print("🚀 High Yield Bond Spread Tracker")
    print("=" * 60)
    
    # Validar configuración
    if not FRED_API_KEY:
        print("❌ ERROR: FRED_API_KEY no configurado")
        return 1
    
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ WARNING: Telegram no configurado - solo se mostrará en logs")
    
    # Verificar salud del sistema
    print("\n🔍 Verificando salud del sistema...")
    verificar_salud_sistema()
    
    try:
        # Obtener datos actuales
        print("\n📡 Obteniendo datos de FRED...")
        datos = obtener_datos_fred(dias=10)
        print(f"✅ Recibidos {len(datos)} registros")
        print(f"   Último dato: {datos[0]['fecha']} = {datos[0]['valor']:.2f}%")
        
        # Cargar estado anterior
        estado_anterior = cargar_estado()
        if estado_anterior:
            print(f"   Dato anterior: {estado_anterior['fecha']} = {estado_anterior['valor']:.2f}%")
        else:
            print("   (No hay dato anterior)")
        
        # Analizar datos
        print("\n🔍 Analizando datos...")
        tiene_alertas, mensaje, es_critico = analizar_datos(datos, estado_anterior)
        
        # Enviar alertas si las hay
        if tiene_alertas and mensaje:
            print("\n⚠️ ALERTAS DETECTADAS:")
            print("-" * 60)
            # Imprimir sin HTML tags para logs
            print(mensaje.replace('<b>', '').replace('</b>', '').replace('<a href=', '\n[Link: ').replace('</a>', ']'))
            print("-" * 60)
            
            if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
                enviar_telegram(mensaje, es_critico)
            else:
                print("\n⚠️ Telegram no configurado - mensaje no enviado")
        else:
            print("✅ No hay alertas - spread dentro de rangos normales")
        
        # Guardar estado actual
        nuevo_estado = {
            'fecha': datos[0]['fecha'],
            'valor': datos[0]['valor'],
            'ultima_ejecucion': datetime.now().isoformat()
        }
        guardar_estado(nuevo_estado)
        print(f"\n💾 Estado guardado: {nuevo_estado['fecha']}")
        
        # Enviar heartbeat semanal si es viernes
        enviar_heartbeat_semanal()
        
        print("\n✅ Ejecución completada exitosamente")
        return 0
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        # Enviar alerta de error por Telegram
        if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
            mensaje_error = (
                f"❌ <b>Error en Bond Spread Tracker</b>\n\n"
                f"Error: {str(e)}\n"
                f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            enviar_telegram(mensaje_error, True)
        return 1


if __name__ == '__main__':
    exit(main())
