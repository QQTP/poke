from flask import Flask, request, jsonify, send_from_directory
import random
from collections import Counter
import os

app = Flask(__name__)

CARD_ORDER = ['7', 'BJ', 'SJ', '5', '2', '3', 'A', 'K', 'Q', 'J', '10', '9', '8', '6', '4']
SUIT_ORDER = ['♠', '♥', '♣', '♦']
SCORED_CARDS = {'5': 5, '10': 10, 'K': 10}

class Card:
    def __init__(self, value, suit=None):
        self.value = value
        self.suit = suit
    def to_dict(self):
        return {'value': self.value, 'suit': self.suit}
    def __str__(self):
        return f"{self.suit if self.suit else ''}{self.value}"
    def __eq__(self, other):
        return self.value == other.value and self.suit == other.suit
    def __hash__(self):
        return hash((self.value, self.suit))

class Game:
    def __init__(self):
        self.deck = self.create_deck()
        self.player_hand = []
        self.ai_hand = []
        self.player_score_cards = []
        self.ai_score_cards = []
        self.last_play = None
        self.last_play_cards = []
        self.last_play_player = None
        self.round_score_cards = []
        self.current_player = 'player'
        self.deal()
    def create_deck(self):
        deck = []
        for value in CARD_ORDER:
            if value == 'BJ':
                deck.append(Card('BJ'))
            elif value == 'SJ':
                deck.append(Card('SJ'))
            else:
                for suit in SUIT_ORDER:
                    deck.append(Card(value, suit))
        random.shuffle(deck)
        return deck
    def deal(self):
        for _ in range(5):
            self.player_hand.append(self.deck.pop())
            self.ai_hand.append(self.deck.pop())
    def refill_hands(self):
        while len(self.player_hand) < 5 and self.deck:
            self.player_hand.append(self.deck.pop())
        while len(self.ai_hand) < 5 and self.deck:
            self.ai_hand.append(self.deck.pop())
    def get_score(self, score_cards):
        return sum(SCORED_CARDS.get(card.value, 0) for card in score_cards)
    def remove_cards(self, hand, cards):
        for card in cards:
            for h in hand:
                if h == card:
                    hand.remove(h)
                    break
    def ai_choose_cards(self):
        hand = sorted(self.ai_hand, key=lambda c: (CARD_ORDER.index(c.value), SUIT_ORDER.index(c.suit) if c.suit else -1))
        score_cards = [card for card in hand if card.value in SCORED_CARDS]
        if score_cards:
            return [score_cards[0]]
        return [hand[0]] if hand else []
    def play_cards(self, player, cards):
        if player == 'player':
            self.remove_cards(self.player_hand, cards)
            self.last_play_player = 'player'
        else:
            self.remove_cards(self.ai_hand, cards)
            self.last_play_player = 'ai'
        self.last_play = '单张'
        self.last_play_cards = cards
        self.round_score_cards = [card for card in cards if card.value in SCORED_CARDS]
        if self.round_score_cards:
            if self.last_play_player == 'player':
                self.player_score_cards.extend(self.round_score_cards)
            else:
                self.ai_score_cards.extend(self.round_score_cards)
        self.refill_hands()
        self.current_player = 'ai' if player == 'player' else 'player'
    def is_game_end(self):
        return not self.player_hand and not self.ai_hand and not self.deck

game_instance = None

@app.route('/api/start', methods=['POST'])
def start_game():
    global game_instance
    game_instance = Game()
    return jsonify({
        'playerHand': [c.to_dict() for c in game_instance.player_hand],
        'aiHandCount': len(game_instance.ai_hand),
        'playerScore': game_instance.get_score(game_instance.player_score_cards),
        'aiScore': game_instance.get_score(game_instance.ai_score_cards),
        'currentPlayer': game_instance.current_player
    })

@app.route('/api/play', methods=['POST'])
def play():
    global game_instance
    data = request.json
    cards = [Card(c['value'], c.get('suit')) for c in data['cards']]
    game_instance.play_cards('player', cards)
    ai_cards = []
    if not game_instance.is_game_end() and game_instance.current_player == 'ai':
        ai_cards = game_instance.ai_choose_cards()
        game_instance.play_cards('ai', ai_cards)
    return jsonify({
        'playerHand': [c.to_dict() for c in game_instance.player_hand],
        'aiHandCount': len(game_instance.ai_hand),
        'playerScore': game_instance.get_score(game_instance.player_score_cards),
        'aiScore': game_instance.get_score(game_instance.ai_score_cards),
        'aiCards': [c.to_dict() for c in ai_cards],
        'gameEnd': game_instance.is_game_end(),
        'winner': get_winner() if game_instance.is_game_end() else None
    })

@app.route('/api/pass', methods=['POST'])
def pass_turn():
    global game_instance
    ai_cards = []
    if not game_instance.is_game_end() and game_instance.current_player == 'ai':
        ai_cards = game_instance.ai_choose_cards()
        game_instance.play_cards('ai', ai_cards)
    return jsonify({
        'playerHand': [c.to_dict() for c in game_instance.player_hand],
        'aiHandCount': len(game_instance.ai_hand),
        'playerScore': game_instance.get_score(game_instance.player_score_cards),
        'aiScore': game_instance.get_score(game_instance.ai_score_cards),
        'aiCards': [c.to_dict() for c in ai_cards],
        'gameEnd': game_instance.is_game_end(),
        'winner': get_winner() if game_instance.is_game_end() else None
    })

@app.route('/')
def index():
    return send_from_directory(os.path.dirname(__file__), 'poke_game.html')

@app.route('/<path:path>')
def static_proxy(path):
    return send_from_directory(os.path.dirname(__file__), path)

def get_winner():
    p = game_instance.get_score(game_instance.player_score_cards)
    a = game_instance.get_score(game_instance.ai_score_cards)
    if p > a:
        return '你'
    elif a > p:
        return 'AI'
    else:
        return '平局'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
