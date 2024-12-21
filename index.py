from flask import Flask, render_template, request, g, redirect
import sqlite3
import requests
import math
import matplotlib.pyplot as plt
import matplotlib
import os
matplotlib.use('Agg')


app = Flask(__name__)
database = 'datafile.db'

def get_db():
    if not hasattr(g, 'sqlite_db'):
        g.sqlite_db = sqlite3.connect(database)
    return g.sqlite_db

@app.teardown_appcontext
def close_db(exception):
    if hasattr(g, 'sqlite_db'):
        g.sqlite_db.close()

@app.route('/')
def home():
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM cash")
    cash_result = cursor.fetchall()
    taiwanese_dollars = 0
    us_dollars = 0
    for row in cash_result:
        taiwanese_dollars += row[1]
        us_dollars += row[2]
        print(row)
    # get the exchange rate
    r = requests.get('https://tw.rter.info/capi.php')
    currency = r.json()
    total = math.floor(taiwanese_dollars + us_dollars * currency['USDTWD']['Exrate'])

    result = cursor.execute("SELECT * FROM stock")
    stock_result = result.fetchall()

    unique_stock_list = []
    for row in stock_result:
      if row[1] not in unique_stock_list:
        unique_stock_list.append(row[1])

    # calculate the stock price
    total_stock_value = 0
    stock_info = []
    
    for stock_id in unique_stock_list:
        result = cursor.execute("SELECT * FROM stock WHERE stock_id = ?", (stock_id,))
        result = result.fetchall()
        stock_cost = 0 # each stock cost
        shares = 0 # each stock shares
        for d in result:
            print('d', d)
            stock_cost += d[3] + d[4] + d[5]
            shares += d[2]
        
        # Get the current stock price
        r = requests.get(f'https://www.twse.com.tw/exchangeReport/STOCK_DAY?response=json&stockNo={stock_id}')
        data = r.json()
        price_array = data['data']
        current_price = float(price_array[len(price_array) - 1][6].replace(',', ''))

        # Each stock value
        total_value = int(current_price * shares)
        total_stock_value += total_value

        # Each stock average cost
        average_cost = round(stock_cost / shares, 2)
        print('average_cost', average_cost)
        # Each stock profit
        rate_of_return = round((total_value - stock_cost) * 100 / stock_cost, 2)
        print('rate_of_return', rate_of_return, total_value, stock_cost)
        stock_info.append({
            'stock_id': stock_id,
            'stock_cost': stock_cost,
            'shares': shares,
            'current_price': current_price,
            'total_value': total_value,
            'average_cost': average_cost,
            'rate_of_return': rate_of_return
        })

        print('current_price', type(current_price), current_price)

    for stock in stock_info:
        stock['value_percentage'] = round(stock['total_value'] * 100 / total_stock_value, 2)

    # generate stock pie chart
    if len(unique_stock_list) != 0:
        labels = tuple(unique_stock_list)
        sizes = [d['total_value'] for d in stock_info]
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.pie(sizes, labels=labels, autopct=None, shadow=None)
        fig.subplots_adjust(top=1, bottom=0, left=0, right=1, hspace=0, wspace=0)
        plt.savefig('static/stock_pie_chart.png', dpi=200)
    else:
        os.remove('static/stock_pie_chart.png')
    # generate cash pie chart
    if us_dollars != 0 or taiwanese_dollars != 0 or total_stock_value != 0:
        labels = ('USD', 'TWD', 'STOCK')
        sizes = (us_dollars * currency['USDTWD']['Exrate'], taiwanese_dollars, total_stock_value)
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.pie(sizes, labels=labels, autopct=None, shadow=None)
        fig.subplots_adjust(top=1, bottom=0, left=0, right=1, hspace=0, wspace=0)
        plt.savefig('static/total_pie_chart.png', dpi=200)
    else:
        os.remove('static/total_pie_chart.png')

    data = {
        "show_stock_pie_chart": os.path.exists('static/stock_pie_chart.png'),
        "show_total_pie_chart": os.path.exists('static/total_pie_chart.png'),
        "total": total, "currency": currency['USDTWD']['Exrate'], 'us': us_dollars, 'twd': taiwanese_dollars, 'cash_result': cash_result, 'stock_info': stock_info,}
    print(data)
    
    return render_template('index.html',data=data)

@app.route('/cash')
def cash_form():
    return render_template('cash.html')

@app.route('/cash', methods=['POST'])
def submit_cash():
    # get the data from the form
    taiwanese_dollars = 0
    us_dollars = 0 
    if request.values['taiwanese-dollars'] != '':
        taiwanese_dollars = request.values['taiwanese-dollars']
    if request.values['us-dollars'] != '':
        us_dollars = request.values['us-dollars']
    note = request.values['note']
    date = request.values['date']
    # update the database
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO cash (taiwanese_dollars, us_dollars, note, date_info) VALUES (?, ?, ?, ?)", (taiwanese_dollars, us_dollars, note, date))
    connection.commit()

    # Redirect to the home page
    return redirect('/')

@app.route('/cash-delete', methods=['POST'])
def cash_delete():
    id = request.values['id']
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("DELETE FROM cash WHERE transaction_id = ?", (id,))
    connection.commit()
    return redirect('/')


@app.route('/stock')
def stock_form():
    return render_template('stock.html')

@app.route('/stock', methods=['POST'])
def submit_stock():
    # get stock info, date...
    stock_id = request.values['stock-id']
    stock_num = request.values['stock-num']
    stock_price = request.values['stock-price']
    date = request.values['date']
    processing_fee = request.values['processing-fee'] if request.values['processing-fee'] != '' else 0
    tax = request.values['tax'] if request.values['tax'] != '' else 0

    print(stock_id, stock_num, stock_price, date, processing_fee, tax)
    # update the database
    connection = get_db()
    cursor = connection.cursor()
    cursor.execute("INSERT INTO stock (stock_id, stock_num, stock_price, date_info, processing_fee, tax) VALUES (?, ?, ?, ?, ?, ?)", (stock_id, stock_num, stock_price, date, processing_fee, tax))
    connection.commit()
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)