import os
import httpx

from dotenv import load_dotenv
from telegram import (
    Update,
    KeyboardButton,
    ReplyKeyboardMarkup
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

load_dotenv()

TOKEN = os.getenv("TELEGRAM_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    botao_localizacao = KeyboardButton(
        "📍 Compartilhar localização",
        request_location=True
    )

    botao_cidade = KeyboardButton(
        "✍️ Digitar outra cidade"
    )

    teclado = ReplyKeyboardMarkup(
        [
            [botao_localizacao],
            [botao_cidade]
        ],
        resize_keyboard=True
    )

    await update.message.reply_text(
        "Olá! Sou seu Bot de Clima! 🌤️\n\n"
        "Escolha como deseja consultar o clima:\n\n"
        "📍 Compartilhar sua localização atual (talvez, na versão desktop não esteja disponível).\n"
        "✍️ Digitar o nome de uma cidade do Brasil ou do mundo.\n\n"
        "Exemplo: Campinas, Londres ou Hortolândia.",
        reply_markup=teclado
    )


async def receber_localizacao(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    localizacao = update.message.location

    latitude = localizacao.latitude
    longitude = localizacao.longitude

    await update.message.reply_text(
        "📡 Consultando sua localização..."
    )

    await consultar_clima(
        update,
        latitude,
        longitude,
        "Localização compartilhada"
    )


async def receber_cidade(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    cidade = update.message.text.strip()


    if cidade == "❌ Não, obrigado":

        teclado = ReplyKeyboardMarkup(
            [
                ["📍 Compartilhar localização"],
                ["✍️ Digitar outra cidade"]
            ],
            resize_keyboard=True
        )

        await update.message.reply_text(
            "Obrigado por utilizar o ClimaxBot! 🌤️\n\n"
            "Até a próxima! Se quiser consultar novamente, "
            "é só escolher uma das opções.",
            reply_markup=teclado
        )

        return

    if cidade == "✅ Sim, consultar outra cidade":

        await update.message.reply_text(
            "Digite o nome da cidade que deseja consultar. 🏙️\n\n"
            "Exemplo: Campinas"
        )

        return

    if cidade == "✍️ Digitar outra cidade":

        await update.message.reply_text(
            "Digite o nome da cidade que deseja consultar. 🏙️\n\n"
            "Exemplo: Campinas"
        )

        return

    if not cidade:

        await update.message.reply_text(
            "Digite o nome de uma cidade válida."
        )

        return

    await update.message.reply_text(
        f"🔎 Procurando informações sobre {cidade}..."
    )

    url = "https://geocoding-api.open-meteo.com/v1/search"

    parametros = {
        "name": cidade,
        "count": 1,
        "language": "pt",
        "format": "json"
    }

    try:

        async with httpx.AsyncClient(timeout=15) as cliente:

            resposta = await cliente.get(
                url,
                params=parametros
            )

            resposta.raise_for_status()

            dados = resposta.json()

        resultados = dados.get("results")

        if not resultados:

            await update.message.reply_text(
                "Cidade não encontrada. "
                "Verifique o nome e tente novamente."
            )

            return

        resultado = resultados[0]

        latitude = resultado["latitude"]
        longitude = resultado["longitude"]

        nome = resultado["name"]
        estado = resultado.get("admin1", "")
        pais = resultado.get("country", "")

        local = ", ".join(
            parte for parte in [nome, estado, pais] if parte
        )

        await consultar_clima(
            update,
            latitude,
            longitude,
            local
        )

    except (httpx.HTTPError, KeyError, ValueError):

        await update.message.reply_text(
            "Não foi possível localizar essa cidade. "
            "Tente novamente mais tarde."
        )


async def consultar_clima(
    update: Update,
    latitude: float,
    longitude: float,
    local: str
):

    url = "https://api.open-meteo.com/v1/forecast"

    parametros = {
        "latitude": latitude,
        "longitude": longitude,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "weather_code",
            "wind_speed_10m"
        ],
        "timezone": "auto"
    }

    try:

        async with httpx.AsyncClient(timeout=15) as cliente:

            resposta = await cliente.get(
                url,
                params=parametros
            )

            resposta.raise_for_status()

            dados = resposta.json()

        clima = dados["current"]

        temperatura = clima["temperature_2m"]
        sensacao = clima["apparent_temperature"]
        umidade = clima["relative_humidity_2m"]
        vento = clima["wind_speed_10m"]
        codigo = clima["weather_code"]

        descricao = descrever_clima(codigo)

        mensagem = (
            "🌤️ CLIMA DA SUA REGIÃO\n\n"
            f"📍 Local: {local}\n\n"
            f"🌡️ Temperatura: {temperatura}°C\n"
            f"🥵 Sensação térmica: {sensacao}°C\n"
            f"💧 Umidade: {umidade}%\n"
            f"💨 Vento: {vento} km/h\n\n"
            f"☁️ Condição: {descricao}\n\n"
            "📍 Consulta realizada com sucesso!\n\n"
            "🌎 Quer tentar outra cidade?"
        )

        teclado = ReplyKeyboardMarkup(
            [
                ["✅ Sim, consultar outra cidade"],
                ["❌ Não, obrigado"]
            ],
            resize_keyboard=True
        )

        await update.message.reply_text(
            mensagem,
            reply_markup=teclado
        )

    except (httpx.HTTPError, KeyError, ValueError):

        await update.message.reply_text(
            "Não foi possível consultar o clima. "
            "Tente novamente mais tarde."
        )


def descrever_clima(codigo):

    condicoes = {
        0: "Céu limpo ☀️",
        1: "Predominantemente limpo 🌤️",
        2: "Parcialmente nublado ⛅",
        3: "Nublado ☁️",
        45: "Neblina 🌫️",
        48: "Neblina com geada 🌫️",
        51: "Garoa fraca 🌦️",
        53: "Garoa moderada 🌦️",
        55: "Garoa intensa 🌧️",
        61: "Chuva fraca 🌧️",
        63: "Chuva moderada 🌧️",
        65: "Chuva forte 🌧️",
        71: "Neve fraca ❄️",
        73: "Neve moderada ❄️",
        75: "Neve forte ❄️",
        80: "Pancadas de chuva 🌦️",
        81: "Pancadas moderadas 🌧️",
        82: "Pancadas fortes ⛈️",
        95: "Tempestade ⛈️",
        96: "Tempestade com granizo ⛈️",
        99: "Tempestade forte com granizo ⛈️"
    }

    return condicoes.get(codigo, "Condição não identificada")


def main():

    if not TOKEN:

        raise RuntimeError(
            "Token não encontrado. Verifique o arquivo .env."
        )

    app = Application.builder().token(TOKEN).build()

    app.add_handler(
        CommandHandler("start", start)
    )

    app.add_handler(
        MessageHandler(
            filters.LOCATION,
            receber_localizacao
        )
    )

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            receber_cidade
        )
    )

    print("Bot de clima iniciado!")

    app.run_polling()


if __name__ == "__main__":
    main()
