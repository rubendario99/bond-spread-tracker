#!/usr/bin/env python3
"""
Suite de tests para Bond Spread Tracker
Verifica que todo funcione correctamente sin esperar al horario programado
"""

import os
import sys
import json
import requests
from datetime import datetime

# ===== CONFIGURACIÓN DE TESTS =====
FRED_API_KEY = os.environ.get('FRED_API_KEY', 'e0fae284e34344d19a7be263bd97af33')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', '8116088009:AAEfEZK9WqkvT9JQil_NPAb2PSaBsekC5KA')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID', '77840700')

FRED_SERIES_ID = 'BAMLH0A0HYM2'

# Colores para terminal
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

tests_passed = 0
tests_failed = 0

def print_test(name, passed, message=""):
    """Imprime resultado de un test"""
    global tests_passed, tests_failed
    
    if passed:
        tests_passed += 1
        status = f"{GREEN}✓ PASS{RESET}"
    else:
        tests_failed += 1
        status = f"{RED}✗ FAIL{RESET}"
    
    print(f"{status} | {name}")
    if message:
        print(f"       {message}")


def test_1_fred_api_connection():
    """Test 1: Verificar conexión con FRED API"""
    print(f"\n{BLUE}TEST 1: Conexión con FRED API{RESET}")
    
    try:
        url = f'https://api.stlouisfed.org/fred/series/observations'
        params = {
            'series_id': FRED_SERIES_ID,
            'api_key': FRED_API_KEY,
            'file_type': 'json',
            'limit': 1,
            'sort_order': 'desc'
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        print_test(
            "Conectar a FRED API",
            response.status_code == 200,
            f"Status: {response.status_code}"
        )
        
        return response.status_code == 200
        
    except Exception as e:
        print_test("Conectar a FRED API", False, f"Error: {e}")
        return False


def test_2_fred_data_retrieval():
    """Test 2: Obtener y validar datos de FRED"""
    print(f"\n{BLUE}TEST 2: Recuperación de datos de FRED{RESET}")
    
    try:
        url = f'https://api.stlouisfed.org/fred/series/observations'
        params = {
            'series_id': FRED_SERIES_ID,
            'api_key': FRED_API_KEY,
            'file_type': 'json',
            'limit': 5,
            'sort_order': 'desc'
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        # Test: Respuesta contiene observaciones
        has_observations = 'observations' in data and len(data['observations']) > 0
        print_test(
            "Respuesta contiene datos",
            has_observations,
            f"Observaciones: {len(data.get('observations', []))}"
        )
        
        if not has_observations:
            return False
        
        # Test: Datos más recientes
        latest = data['observations'][0]
        print_test(
            "Datos tienen fecha",
            'date' in latest,
            f"Fecha: {latest.get('date', 'N/A')}"
        )
        
        # Test: Valor es numérico válido
        value = latest.get('value', '.')
        is_numeric = value != '.' and float(value) > 0
        print_test(
            "Valor es numérico válido",
            is_numeric,
            f"Valor: {value}%"
        )
        
        # Test: Valor está en rango razonable (0.5% - 30%)
        if is_numeric:
            val = float(value)
            in_range = 0.5 <= val <= 30.0
            print_test(
                "Valor en rango razonable",
                in_range,
                f"Spread: {val}% (rango: 0.5-30%)"
            )
        
        # Mostrar últimos 5 datos
        print(f"\n  {YELLOW}Últimos 5 datos históricos:{RESET}")
        for i, obs in enumerate(data['observations'][:5]):
            if obs['value'] != '.':
                print(f"  {i+1}. {obs['date']}: {obs['value']}%")
        
        return True
        
    except Exception as e:
        print_test("Recuperar datos de FRED", False, f"Error: {e}")
        return False


def test_3_telegram_connection():
    """Test 3: Verificar conexión con Telegram"""
    print(f"\n{BLUE}TEST 3: Conexión con Telegram Bot API{RESET}")
    
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe'
        response = requests.get(url, timeout=10)
        data = response.json()
        
        print_test(
            "Token de bot válido",
            data.get('ok') == True,
            f"Bot: @{data.get('result', {}).get('username', 'N/A')}"
        )
        
        if data.get('ok'):
            bot_info = data['result']
            print(f"  {YELLOW}Info del bot:{RESET}")
            print(f"  • Nombre: {bot_info.get('first_name')}")
            print(f"  • Username: @{bot_info.get('username')}")
            print(f"  • ID: {bot_info.get('id')}")
        
        return data.get('ok') == True
        
    except Exception as e:
        print_test("Conectar a Telegram API", False, f"Error: {e}")
        return False


def test_4_send_test_message():
    """Test 4: Enviar mensaje de prueba por Telegram"""
    print(f"\n{BLUE}TEST 4: Envío de mensaje de prueba{RESET}")
    
    try:
        url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
        
        mensaje = (
            f"🧪 <b>TEST DE BOT - Bond Spread Tracker</b>\n\n"
            f"✅ El bot está funcionando correctamente\n\n"
            f"📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"🤖 Este es un mensaje de prueba\n\n"
            f"<i>Si recibes este mensaje, todo está configurado correctamente</i>"
        )
        
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': mensaje,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        data = response.json()
        
        success = data.get('ok') == True
        print_test(
            "Enviar mensaje de prueba",
            success,
            "✅ Revisa tu Telegram!" if success else f"Error: {data.get('description', 'Unknown')}"
        )
        
        return success
        
    except Exception as e:
        print_test("Enviar mensaje de prueba", False, f"Error: {e}")
        return False


def test_5_threshold_logic():
    """Test 5: Verificar lógica de umbrales"""
    print(f"\n{BLUE}TEST 5: Lógica de detección de alertas{RESET}")
    
    # Simular diferentes escenarios
    test_cases = [
        {
            'name': 'Cambio brusco positivo',
            'actual': 5.0,
            'anterior': 4.5,
            'should_alert': True,  # Cambio de 0.5% > 0.15%
        },
        {
            'name': 'Cambio pequeño',
            'actual': 4.5,
            'anterior': 4.4,
            'should_alert': False,  # Cambio de 0.1% < 0.15%
        },
        {
            'name': 'Nivel crítico alcanzado',
            'actual': 6.6,
            'anterior': 6.4,
            'should_alert': True,  # Supera 6.5%
        },
        {
            'name': 'Nivel alto pero no crítico',
            'actual': 5.5,
            'anterior': 5.4,
            'should_alert': True,  # Supera 5.0%
        },
        {
            'name': 'Normal, sin alertas',
            'actual': 3.5,
            'anterior': 3.4,
            'should_alert': False,  # Normal
        },
    ]
    
    UMBRAL_CAMBIO = 0.15
    UMBRAL_ALTO = 5.0
    UMBRAL_CRITICO = 6.5
    
    for case in test_cases:
        actual = case['actual']
        anterior = case['anterior']
        cambio = abs(actual - anterior)
        
        should_alert = (
            cambio >= UMBRAL_CAMBIO or
            actual >= UMBRAL_ALTO or
            actual >= UMBRAL_CRITICO
        )
        
        passed = should_alert == case['should_alert']
        
        print_test(
            case['name'],
            passed,
            f"Actual: {actual}%, Anterior: {anterior}%, Cambio: {cambio}%, Alerta: {should_alert}"
        )
    
    return True


def test_6_simulate_alert():
    """Test 6: Simular alerta realista"""
    print(f"\n{BLUE}TEST 6: Simulación de alerta real{RESET}")
    
    try:
        # Obtener datos reales
        url = f'https://api.stlouisfed.org/fred/series/observations'
        params = {
            'series_id': FRED_SERIES_ID,
            'api_key': FRED_API_KEY,
            'file_type': 'json',
            'limit': 2,
            'sort_order': 'desc'
        }
        
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        
        if len(data['observations']) >= 2:
            actual_obs = data['observations'][0]
            anterior_obs = data['observations'][1]
            
            if actual_obs['value'] != '.' and anterior_obs['value'] != '.':
                actual = float(actual_obs['value'])
                anterior = float(anterior_obs['value'])
                cambio = actual - anterior
                cambio_pct = (cambio / anterior) * 100 if anterior != 0 else 0
                
                # Construir mensaje simulado
                mensaje = (
                    f"📊 <b>SIMULACIÓN - Alerta con datos reales</b>\n\n"
                    f"📅 Fecha actual: {actual_obs['date']}\n"
                    f"📈 Spread actual: <b>{actual:.2f}%</b>\n"
                    f"📉 Spread anterior: {anterior:.2f}% ({anterior_obs['date']})\n"
                    f"{'🔺' if cambio > 0 else '🔻'} Cambio: {'+' if cambio > 0 else ''}{cambio:.2f}% "
                    f"({'+' if cambio_pct > 0 else ''}{cambio_pct:.1f}%)\n\n"
                )
                
                # Evaluar condiciones
                alertas = []
                if abs(cambio) >= 0.15:
                    alertas.append(f"{'📈' if cambio > 0 else '📉'} Cambio brusco detectado")
                if actual >= 6.5:
                    alertas.append(f"🚨 Nivel CRÍTICO (>{6.5}%)")
                elif actual >= 5.0:
                    alertas.append(f"⚠️ Nivel ALTO (>{5.0}%)")
                
                if alertas:
                    mensaje += "🚨 <b>Alertas que se activarían:</b>\n"
                    for alerta in alertas:
                        mensaje += f"• {alerta}\n"
                else:
                    mensaje += "✅ No se activarían alertas (valores normales)\n"
                
                mensaje += f"\n<i>Esta es una simulación con datos reales del {actual_obs['date']}</i>"
                
                # Enviar simulación
                url_tg = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
                payload = {
                    'chat_id': TELEGRAM_CHAT_ID,
                    'text': mensaje,
                    'parse_mode': 'HTML'
                }
                
                response = requests.post(url_tg, json=payload, timeout=10)
                success = response.json().get('ok') == True
                
                print_test(
                    "Enviar alerta simulada con datos reales",
                    success,
                    f"Spread actual: {actual:.2f}%, {'Alertas: ' + str(len(alertas)) if alertas else 'Sin alertas'}"
                )
                
                return success
        
        print_test("Simular alerta", False, "No hay suficientes datos")
        return False
        
    except Exception as e:
        print_test("Simular alerta", False, f"Error: {e}")
        return False


def test_7_force_alert_scenario():
    """Test 7: Forzar escenario de alerta crítica"""
    print(f"\n{BLUE}TEST 7: Escenario de alerta crítica (forzado){RESET}")
    
    try:
        # Escenario simulado de crisis
        mensaje = (
            f"🚨🚨🚨\n"
            f"📊 <b>TEST - Alerta CRÍTICA Simulada</b>\n\n"
            f"📅 Fecha simulada: {datetime.now().strftime('%Y-%m-%d')}\n"
            f"📈 Spread simulado: <b>7.50%</b>\n"
            f"📉 Spread anterior: 5.20%\n"
            f"🔺 Cambio: +2.30% (+44.2%)\n\n"
            f"🚨 <b>ALERTAS (SIMULADAS):</b>\n\n"
            f"• 📈 <b>SUBIDA BRUSCA</b>\n"
            f"   Cambio: +2.30% (+44.2%)\n\n"
            f"• 🚨 <b>NIVEL CRÍTICO</b>\n"
            f"   Spread en 7.50% (umbral: 6.5%)\n\n"
            f"• ⬆️ Spread cruzó umbral CRÍTICO de <b>6.5%</b>\n\n"
            f"📊 Contexto histórico:\n"
            f"   • Normal: 3-5%\n"
            f"   • Crisis 2008: >20%\n"
            f"   • COVID-19: ~10%\n\n"
            f"<i>⚠️ Esto es un TEST - Datos simulados para verificar alertas críticas</i>"
        )
        
        url = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage'
        payload = {
            'chat_id': TELEGRAM_CHAT_ID,
            'text': mensaje,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(url, json=payload, timeout=10)
        success = response.json().get('ok') == True
        
        print_test(
            "Enviar alerta crítica simulada",
            success,
            "✅ Revisa cómo se vería una alerta de crisis"
        )
        
        return success
        
    except Exception as e:
        print_test("Forzar alerta crítica", False, f"Error: {e}")
        return False


def main():
    """Ejecutar todos los tests"""
    print("=" * 70)
    print(f"{BLUE}🧪 BOND SPREAD TRACKER - SUITE DE TESTS{RESET}")
    print("=" * 70)
    print(f"\n📅 Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Ejecutar tests
    test_1_fred_api_connection()
    test_2_fred_data_retrieval()
    test_3_telegram_connection()
    test_4_send_test_message()
    test_5_threshold_logic()
    test_6_simulate_alert()
    test_7_force_alert_scenario()
    
    # Resumen
    print("\n" + "=" * 70)
    print(f"{BLUE}RESUMEN DE TESTS{RESET}")
    print("=" * 70)
    total = tests_passed + tests_failed
    percentage = (tests_passed / total * 100) if total > 0 else 0
    
    print(f"\n✅ Tests pasados: {GREEN}{tests_passed}{RESET}")
    print(f"❌ Tests fallidos: {RED}{tests_failed}{RESET}")
    print(f"📊 Total: {total}")
    print(f"🎯 Porcentaje de éxito: {percentage:.1f}%\n")
    
    if tests_failed == 0:
        print(f"{GREEN}🎉 ¡TODOS LOS TESTS PASARON!{RESET}")
        print(f"{GREEN}El bot está 100% funcional y listo para usar.{RESET}\n")
        return 0
    else:
        print(f"{RED}⚠️ Algunos tests fallaron. Revisa los errores arriba.{RESET}\n")
        return 1


if __name__ == '__main__':
    exit(main())
