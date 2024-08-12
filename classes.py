from binance.client import Client
import pandas as pd

# API keys for Binance
api_key = 'bf27848553da5308287d7ecf02bc977de1e6f94d56434945991e1cdcbe09a985'
api_secret = '3f913d269ecfe00fabc93d615b32f82510433424ed3dcf5b8c5d654b93e333b9'
client = Client(api_key, api_secret, tld='com', testnet=True)

class Bot:
    def __init__(self, symbol, num_of_decimals, quantity, proportion, tp, n):
        self.symbol = symbol
        self.num_of_decimals = num_of_decimals
        self.quantity = quantity
        self.proportion = proportion
        self.tp = tp
        self.n = n

    def get_balance(self):
        account = client.futures_account()
        df = pd.DataFrame(account['assets'])
        print(df.columns)

    def sell_limit(self, symbol, quantity, price):
        order = client.futures_create_order(
            symbol=symbol,
            side=Client.SIDE_SELL,
            type=Client.FUTURE_ORDER_TYPE_LIMIT,
            timeInForce=Client.TIME_IN_FORCE_GTC,
            quantity=quantity,
            price=price
        )
        print(f'Sell Limit Order: {order}')

    def buy_limit(self, symbol, quantity, price):
        order = client.futures_create_order(
            symbol=symbol,
            side=Client.SIDE_BUY,
            type=Client.FUTURE_ORDER_TYPE_LIMIT,
            timeInForce=Client.TIME_IN_FORCE_GTC,
            quantity=quantity,
            price=price
        )
        print(f'Buy Limit Order: {order}')

    def close_orders(self, symbol):
        open_orders = client.futures_get_open_orders(symbol=symbol)
        df = pd.DataFrame(open_orders)
        for i in df.index:
            client.futures_cancel_order(symbol=symbol, orderId=df['orderId'][i])
        print(f'Closed all orders for {symbol}')

    def close_buy_orders(self, symbol):
        open_orders = client.futures_get_open_orders(symbol=symbol)
        df = pd.DataFrame(open_orders)
        df = df.loc[df['side'] == 'BUY']
        for i in df.index:
            client.futures_cancel_order(symbol=symbol, orderId=df['orderId'][i])
        print(f'Closed all buy orders for {symbol}')

    def close_sell_orders(self, symbol):
        open_orders = client.futures_get_open_orders(symbol=symbol)
        df = pd.DataFrame(open_orders)
        df = df.loc[df['side'] == 'SELL']
        for i in df.index:
            client.futures_cancel_order(symbol=symbol, orderId=df['orderId'][i])
        print(f'Closed all sell orders for {symbol}')

    def get_direction(self, symbol):
        position_info = client.futures_position_information(symbol=symbol)
        df = pd.DataFrame(position_info)
        df['positionAmt'] = pd.to_numeric(df['positionAmt'])

        if df['positionAmt'][0] > 0:
            return "LONG"
        elif df['positionAmt'][0] < 0:
            return "SHORT"
        else:
            return "FLAT"

    def get_mark_price(self, symbol):
        ticker = client.get_symbol_ticker(symbol=symbol)
        price = float(ticker['price'])
        return price

    def draw_grid(self, n):
        pct_change = 1
        adj_sell = 1.2
        current_price = self.get_mark_price(self.symbol)
        print(f'Current Price: {current_price}')

        # Place sell limit orders
        for i in range(n):
            sell_price = float(round(current_price*(1 + pct_change*adj_sell*self.proportion/100), self.num_of_decimals))
            self.sell_limit(self.symbol, self.quantity, sell_price)
            pct_change += 1
            adj_sell += 0.2
        
        pct_change = -1
        adj_buy = 1.2
        current_price = self.get_mark_price(self.symbol)

        # Place buy limit orders
        for i in range(n):
            buy_price = float(round(current_price*(1 + pct_change*adj_sell*self.proportion/100), self.num_of_decimals))
            self.buy_limit(self.symbol, self.quantity, buy_price)
            pct_change -= 1
            adj_buy += 0.2

    def calculate_tp_level(self, symbol, tp):
        try:
            position_info = client.futures_position_information(symbol=symbol)
            df = pd.DataFrame(position_info)
            df['positionAmt'] = pd.to_numeric(df['positionAmt'])
            df = df.loc[df['positionAmt'] != 0]

            t_margin = float(df['entryPrice'][0])*abs(float(df['positionAmt'][0]))/float(df['leverage'][0])
            profit = float(t_margin*tp/100)
            price = round(float(df['entryPrice'][0]) + profit/float(df['positionAmt'][0]), self.num_of_decimals)
            t_position_amt = abs(float(df['positionAmt'][0]))
            
            print(f'Calculated TP Level: Price={price}, Quantity={t_position_amt}')
            return price, t_position_amt
        except Exception as e:
            print(f'Error calculating TP level: {e}')
            pass


    def place_tp_order(self, symbol, price, t_position_amt, direction):
        try:
            if direction == 'LONG':
                self.sell_limit(symbol, t_position_amt, price)
            elif direction == 'SHORT':
                self.buy_limit(symbol, t_position_amt, price)
            print(f'Placed TP Order: Direction={direction}, Price={price}, Quantity={t_position_amt}')
        except Exception as e:
            print(f'Error placing TP order: {e}')
            self.place_tp_order(symbol, price, t_position_amt, direction)

    
    def run(self):
        while True:
            open_orders = client.futures_get_open_orders(symbol=self.symbol)
            df1 = pd.DataFrame(open_orders)

            if len(df1) == 0:
                print('Drawing grid of orders...')
                self.draw_grid(self.n)

            position_info = client.futures_position_information(symbol=self.symbol)
            df2 = pd.DataFrame(position_info)
            df2['positionAmt'] = pd.to_numeric(df2['positionAmt'])
            df2 = df2.loc[df2['positionAmt'] != 0]

            if len(df2) > 0:
                direction = self.get_direction(self.symbol)
                print(f'Direction: {direction}')
                try:
                    if direction == 'LONG':
                        print(f'Closing sell orders...')
                        self.close_sell_orders(self.symbol)
                    elif direction == 'SHORT':
                        print(f'Closing buy orders...')
                        self.close_buy_orders(self.symbol)
                except Exception as e:
                    print(f'Error closing orders: {e}')
                    pass

                price0, t_position_amt0 = self.calculate_tp_level(self.symbol, self.tp)
                self.place_tp_order(self.symbol, price0, t_position_amt0, direction)
                is_ok = True

                while is_ok:
                    try:
                        price1, t_position_amt1 = self.calculate_tp_level(self.symbol, self.tp)
                        if price1 != price0 or t_position_amt1 != t_position_amt0:
                            if direction == 'LONG':
                                self.close_sell_orders(self.symbol)
                            elif direction == 'SHORT':
                                self.close_buy_orders(self.symbol)
                            self.place_tp_order(self.symbol, price1, t_position_amt1, direction)
                            price0 = price1
                            t_position_amt0 = t_position_amt1
                    except Exception as e:
                        print(f'Error updating TP order: {e}')
                        pass

                    position_info = client.futures_position_information(symbol=self.symbol)
                    df2 = pd.DataFrame(position_info)
                    df2['positionAmt'] = pd.to_numeric(df2['positionAmt'])
                    df2 = df2.loc[df2['positionAmt'] != 0]

                    if len(df2) == 0:
                        try:
                            self.close_orders(self.symbol)
                            is_ok = False
                        except Exception as e:
                            print(f'Error closing all orders: {e}')
                            pass
