import logging
import uuid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

shops = {
    "shop1": {
        "owner_id": "OWNER/BOT GROUP ID",  
        "items": [
            {"name": "NAME", "tag": "TAGS", "price": PRICE, "image": "IMAGEURL"},
        ],
    },
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Welcome to the shop bot! Use /shop <shop_id> to view items.')

async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args or len(context.args) != 1:
        await update.message.reply_text('Please provide a shop ID. Usage: /shop <shop_id>')
        return

    shop_id = context.args[0]
    if shop_id not in shops:
        await update.message.reply_text('Shop not found. Please try again with a valid shop ID.')
        return

    context.user_data['current_shop'] = shop_id
    context.user_data['current_item'] = 0
    await display_item(update, context)

async def display_item(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    shop_id = context.user_data['current_shop']
    item_index = context.user_data['current_item']
    items = shops[shop_id]['items']

    if 0 <= item_index < len(items):
        item = items[item_index]
        caption = f"*{item['name']}*\n*Type*: {item['tag']}\n*Price: ${item['price']}*"

        keyboard = [
            [
                InlineKeyboardButton("⬅️ Back", callback_data="back"),
                InlineKeyboardButton("➡️ Next", callback_data="next"),
            ],
            [
                InlineKeyboardButton("🛒 Add to Cart", callback_data="add_to_cart"),
                InlineKeyboardButton("💳 Checkout", callback_data="checkout"),
            ],
            [
                InlineKeyboardButton("❌ Exit", callback_data="exit"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.callback_query:
            await update.callback_query.message.edit_media(
                media=InputMediaPhoto(media=item['image'], caption=caption, parse_mode=ParseMode.MARKDOWN),
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_photo(
                photo=item['image'],
                caption=caption,
                reply_markup=reply_markup,
                parse_mode=ParseMode.MARKDOWN
            )
    else:
        await update.message.reply_text('No more items in this shop.')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == "back":
        context.user_data['current_item'] = max(0, context.user_data['current_item'] - 1)
        await display_item(update, context)
    elif query.data == "next":
        context.user_data['current_item'] = min(len(shops[context.user_data['current_shop']]['items']) - 1, context.user_data['current_item'] + 1)
        await display_item(update, context)
    elif query.data == "add_to_cart":
        shop_id = context.user_data['current_shop']
        item_index = context.user_data['current_item']
        item = shops[shop_id]['items'][item_index]
        if 'cart' not in context.user_data:
            context.user_data['cart'] = []
        context.user_data['cart'].append(item)
        await query.message.reply_text(f"Added {item['name']} to your cart!")
        await display_item(update, context)
    elif query.data == "checkout":
        await start_checkout(update, context)
    elif query.data == "exit":
        await query.message.edit_caption("Thank you for shopping with us!")
        return

async def start_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if 'cart' not in context.user_data or not context.user_data['cart']:
        await update.callback_query.message.reply_text("Your cart is empty. Add some items before checking out.")
        return

    total_price = sum(item['price'] for item in context.user_data['cart'])
    cart_contents = "\n".join([f"{item['name']} - ${item['price']}" for item in context.user_data['cart']])
    
    message = f"Your cart contains:\n\n{cart_contents}\n\nTotal: ${total_price}\n\nPlease enter your delivery address:"
    await update.callback_query.message.reply_text(message)
    context.user_data['checkout_state'] = 'waiting_for_address'

async def handle_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get('checkout_state') != 'waiting_for_address':
        return

    address = update.message.text
    context.user_data['address'] = address
    
    transaction_id = str(uuid.uuid4())
    context.user_data['transaction_id'] = transaction_id

    shop_id = context.user_data['current_shop']
    owner_id = shops[shop_id]['owner_id']
    order_message = f"New order!\n\nTransaction ID: {transaction_id}\n\nItems:\n"
    order_message += "\n".join([f"{item['name']} - ${item['price']}" for item in context.user_data['cart']])
    order_message += f"\n\nTotal: ${sum(item['price'] for item in context.user_data['cart'])}"
    order_message += f"\n\nDelivery Address: {address}"

    await context.bot.send_message(chat_id=owner_id, text=order_message)

    # Display receipt
    receipt = f"Thank you for your order!\n\nTransaction ID: {transaction_id}\n\nItems:\n"
    receipt += "\n".join([f"{item['name']} - ${item['price']}" for item in context.user_data['cart']])
    receipt += f"\n\nTotal: ${sum(item['price'] for item in context.user_data['cart'])}"
    receipt += f"\n\nDelivery Address: {address}"

    await update.message.reply_text(receipt)

    # Clear the cart and checkout state
    context.user_data['cart'] = []
    context.user_data['checkout_state'] = None

def main() -> None:
    application = Application.builder().token('BOTID').build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("shop", shop))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_address))

    application.run_polling()

if __name__ == '__main__':
    main()
