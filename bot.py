import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
    CommandHandler
)

ARQUIVO = "dados.json"

# ======================
# Utilidades
# ======================

def carregar():
    try:
        with open(ARQUIVO, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def salvar(dados):
    with open(ARQUIVO, "w", encoding="utf-8") as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

def barra(p):
    total = 10
    preenchido = int((p / 100) * total)
    return "🟩" * preenchido + "🟨" * (1 if p < 100 and preenchido < total else 0) + "⬜" * (total - preenchido - (1 if p < 100 and preenchido < total else 0))

def status(p):
    if p == 100:
        return "🏆 *CONCLUÍDA*"
    elif p >= 70:
        return "🚀 *QUASE LÁ*"
    elif p >= 30:
        return "🔥 *EM PROGRESSO*"
    else:
        return "⚠️ *EM ALERTA*"

# ======================
# TELAS
# ======================

def tela_pessoas():
    dados = carregar()
    texto = "👥 *ESCOLHA A PESSOA*\n\n"
    botoes = []

    if dados:
        for nome in dados:
            botoes.append([
                InlineKeyboardButton(nome, callback_data=f"pessoa|{nome}")
            ])
    else:
        texto += "❌ Nenhuma pessoa cadastrada.\n\n"

    botoes.append([InlineKeyboardButton("➕ Nova Pessoa", callback_data="nova_pessoa")])
    return texto, InlineKeyboardMarkup(botoes)

def tela_propostas(pessoa):
    dados = carregar()
    propostas = dados.get(pessoa, {})

    texto = f"📌 *PROPOSTAS DE {pessoa}*\n\n"
    botoes = []

    if propostas:
        for nome, p in propostas.items():
            texto += f"🎯 *{nome}*\n{barra(p)} {p}%\n{status(p)}\n\n"
            botoes.append([
                InlineKeyboardButton(nome, callback_data=f"select|{nome}")
            ])
    else:
        texto += "❌ Nenhuma proposta criada.\n\n"

    botoes.append([InlineKeyboardButton("➕ Nova Proposta", callback_data="nova_proposta")])
    botoes.append([InlineKeyboardButton("⬅️ Trocar Pessoa", callback_data="voltar_pessoas")])

    return texto, InlineKeyboardMarkup(botoes)

def tela_proposta(pessoa, proposta):
    dados = carregar()
    p = dados[pessoa][proposta]

    texto = (
        f"🎯 *{proposta}*\n\n"
        f"{barra(p)} {p}%\n\n"
        f"{status(p)}"
    )

    teclado = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("+5 XP", callback_data="update|5"),
            InlineKeyboardButton("+10 XP", callback_data="update|10"),
            InlineKeyboardButton("-5 XP", callback_data="update|-5"),
        ],
        [
            InlineKeyboardButton("🔄 Resetar", callback_data="reset")
        ],
        [
            InlineKeyboardButton("🗑️ Remover", callback_data="delete|ask")
        ],
        [
            InlineKeyboardButton("⬅️ Voltar", callback_data="voltar_propostas")
        ]
    ])

    return texto, teclado

def tela_confirmar_remocao(proposta):
    texto = (
        f"❗ *CONFIRMAR REMOÇÃO*\n\n"
        f"Remover a proposta:\n"
        f"*{proposta}*?\n\n"
        "⚠️ Ação irreversível."
    )

    teclado = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Sim", callback_data="delete|confirm"),
            InlineKeyboardButton("❌ Cancelar", callback_data="delete|cancel")
        ]
    ])

    return texto, teclado

# ======================
# COMANDOS
# ======================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto, teclado = tela_pessoas()
    await update.message.reply_text(texto, reply_markup=teclado, parse_mode="Markdown")

async def receber_texto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dados = carregar()
    texto = update.message.text

    if context.user_data.get("criando_pessoa"):
        dados[texto] = {}
        salvar(dados)
        context.user_data["criando_pessoa"] = False
        msg, kb = tela_pessoas()
        await update.message.reply_text(f"✅ Pessoa *{texto}* criada!\n\n{msg}", reply_markup=kb, parse_mode="Markdown")

    elif context.user_data.get("criando_proposta"):
        pessoa = context.user_data["pessoa"]
        dados[pessoa][texto] = 0
        salvar(dados)
        context.user_data["criando_proposta"] = False
        msg, kb = tela_propostas(pessoa)
        await update.message.reply_text(f"✅ Proposta *{texto}* criada!\n\n{msg}", reply_markup=kb, parse_mode="Markdown")

# ======================
# BOTÕES
# ======================

async def botoes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    dados = carregar()
    acao = query.data

    if acao == "nova_pessoa":
        context.user_data["criando_pessoa"] = True
        await query.message.reply_text("✍️ Digite o nome da nova pessoa:")

    elif acao.startswith("pessoa|"):
        pessoa = acao.split("|")[1]
        context.user_data["pessoa"] = pessoa
        texto, kb = tela_propostas(pessoa)
        await query.edit_message_text(texto, reply_markup=kb, parse_mode="Markdown")

    elif acao == "nova_proposta":
        context.user_data["criando_proposta"] = True
        await query.message.reply_text("✍️ Digite o nome da nova proposta:")

    elif acao.startswith("select|"):
        proposta = acao.split("|")[1]
        context.user_data["proposta"] = proposta
        pessoa = context.user_data["pessoa"]
        texto, kb = tela_proposta(pessoa, proposta)
        await query.edit_message_text(texto, reply_markup=kb, parse_mode="Markdown")

    elif acao.startswith("update|"):
        delta = int(acao.split("|")[1])
        pessoa = context.user_data["pessoa"]
        proposta = context.user_data["proposta"]
        dados[pessoa][proposta] = max(0, min(100, dados[pessoa][proposta] + delta))
        salvar(dados)
        texto, kb = tela_proposta(pessoa, proposta)
        await query.edit_message_text(texto, reply_markup=kb, parse_mode="Markdown")

    elif acao == "reset":
        pessoa = context.user_data["pessoa"]
        proposta = context.user_data["proposta"]
        dados[pessoa][proposta] = 0
        salvar(dados)
        texto, kb = tela_proposta(pessoa, proposta)
        await query.edit_message_text(texto, reply_markup=kb, parse_mode="Markdown")

    elif acao == "delete|ask":
        proposta = context.user_data["proposta"]
        texto, kb = tela_confirmar_remocao(proposta)
        await query.edit_message_text(texto, reply_markup=kb, parse_mode="Markdown")

    elif acao == "delete|confirm":
        pessoa = context.user_data["pessoa"]
        proposta = context.user_data["proposta"]
        del dados[pessoa][proposta]
        salvar(dados)
        texto, kb = tela_propostas(pessoa)
        await query.edit_message_text(texto, reply_markup=kb, parse_mode="Markdown")

    elif acao == "delete|cancel":
        pessoa = context.user_data["pessoa"]
        proposta = context.user_data["proposta"]
        texto, kb = tela_proposta(pessoa, proposta)
        await query.edit_message_text(texto, reply_markup=kb, parse_mode="Markdown")

    elif acao == "voltar_propostas":
        pessoa = context.user_data["pessoa"]
        texto, kb = tela_propostas(pessoa)
        await query.edit_message_text(texto, reply_markup=kb, parse_mode="Markdown")

    elif acao == "voltar_pessoas":
        texto, kb = tela_pessoas()
        await query.edit_message_text(texto, reply_markup=kb, parse_mode="Markdown")

# ======================
# INIT
# ======================

app = ApplicationBuilder().token("8236401281:AAEUcGo2msY6QMAPVSwLTaQ-CTQxjHT2njQ").build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receber_texto))
app.add_handler(CallbackQueryHandler(botoes))

print("🤖 Bot EJ com pessoas e propostas rodando...")
app.run_polling()
