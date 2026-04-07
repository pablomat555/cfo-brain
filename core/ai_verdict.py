import os
from pathlib import Path
from typing import Optional
import httpx
from loguru import logger

from core.models import PeriodReport


def generate_verdict(report: PeriodReport, strategy: str) -> str:
    """
    Генерирует AI-вердикт на основе финансового отчёта и стратегии.
    
    Использует OpenRouter API. Если API ключ не задан, возвращает fallback текст.
    
    Args:
        report: PeriodReport с финансовыми данными
        strategy: Текст стратегии из STRATEGY.md
        
    Returns:
        Строка с AI анализом или fallback сообщением
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        logger.warning("OPENROUTER_API_KEY not set, returning fallback verdict")
        return "AI analysis unavailable (no API key). Financial report generated successfully."
    
    # Подготовка промпта с учётом мультивалютной агрегации
    currency_info = ""
    if report.rate_type == "manual" and report.rate:
        currency_info = f"Курс конвертации: $1 = ₴{report.rate} (manual, приблизительно)\n"
    elif report.rate_type == "split" and report.currency_breakdown:
        currency_info = "Разбивка по валютам:\n"
        for curr, data in report.currency_breakdown.items():
            currency_info += f"- {curr}: доходы {data['total_income']}, расходы {data['total_expenses']}, сбережения {data['net_savings']}\n"
    
    # Подготовка промпта
    prompt = f"""
Ты финансовый аналитик. Проанализируй месячный финансовый отчёт и дай рекомендации на основе стратегии.

ФИНАНСОВЫЙ ОТЧЁТ:
- Доходы: {report.total_income} {report.currency}
- Расходы: {report.total_expenses} {report.currency}
- Чистые сбережения: {report.net_savings} {report.currency}
- Норма сбережений: {report.savings_rate:.1f}%
- Burn rate: {report.burn_rate} {report.currency}
{currency_info}
- Топ категорий расходов: {list(report.by_category.items())[:5]}
- Топ аккаунтов: {list(report.by_account.items())[:3]}
- Топ-5 расходов: {report.top_expenses[:3] if report.top_expenses else 'нет данных'}

СТРАТЕГИЯ:
{strategy[:2000]}  # Ограничиваем длину

АНАЛИЗ И РЕКОМЕНДАЦИИ:
1. Оцените соответствие отчёта стратегии
2. Выявите проблемные зоны
3. Дайте конкретные рекомендации на следующий месяц
4. Оцените риски

Ответ должен быть кратким, конкретным, на русском языке, максимум 500 слов.
"""
    
    try:
        # Вызов OpenRouter API
        response = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://cfo-brain.local",  # Optional
                "X-Title": "CFO Brain"  # Optional
            },
            json={
                "model": "openai/gpt-3.5-turbo",  # Можно изменить на другой модель
                "messages": [
                    {"role": "system", "content": "Ты опытный финансовый аналитик. Давай чёткие, практические рекомендации на русском языке."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1000,
                "temperature": 0.7
            },
            timeout=30.0
        )
        
        if response.status_code == 200:
            data = response.json()
            verdict = data["choices"][0]["message"]["content"]
            logger.info("AI verdict generated successfully")
            return verdict
        else:
            logger.error(f"OpenRouter API error: {response.status_code} - {response.text}")
            return f"AI analysis failed (API error {response.status_code}). Financial report generated successfully."
            
    except httpx.RequestError as e:
        logger.error(f"OpenRouter request failed: {e}")
        return f"AI analysis failed (network error). Financial report generated successfully."
    except Exception as e:
        logger.error(f"Unexpected error in generate_verdict: {e}")
        return f"AI analysis failed (unexpected error). Financial report generated successfully."


def read_strategy_file() -> str:
    """
    Читает файл стратегии STRATEGY.md.
    
    Использует абсолютный путь /app/STRATEGY.md согласно D-09.
    
    Returns:
        Содержимое файла стратегии или fallback текст
    """
    strategy_path = Path("/app/STRATEGY.md")
    try:
        if strategy_path.exists():
            return strategy_path.read_text(encoding="utf-8")
        else:
            logger.warning(f"Strategy file not found at {strategy_path}")
            return "Стратегия не найдена. Пожалуйста, создайте файл STRATEGY.md с финансовой стратегией."
    except Exception as e:
        logger.error(f"Failed to read strategy file: {e}")
        return f"Ошибка чтения стратегии: {e}"