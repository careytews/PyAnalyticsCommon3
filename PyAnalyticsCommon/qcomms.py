import pika
import os
import sys
import time
from prometheus_client import start_http_server, Counter

analytic_name = 'unknown'
analytic_configured = False
sub_setup = False
pub_setup = False
received_counter = None
sent_counter = None

def run_metrics_server():
    start_http_server(8080)

def setup_sub():
    global received_counter
    if received_counter == None:
      received_counter = Counter('events_received', 'number of events analytic has received', ['analytic', 'exchange', 'queue', 'type'])

def setup_pub():
    global sent_counter
    if sent_counter == None:
        sent_counter = Counter('output_events_sent', 'number of events analytic has sent', ['analytic', 'exchange', 'type', 'routing_key'])


class Subscriber:
    def __init__(self, broker=None, queue=None, routing_key=None, exchange=None, exchange_type=None,
                 durable=True, auto_delete=False, exclusive=False, debug=False):

        if not analytic_configured:
            print('ERROR - analytic module has not been configured, some metrics may have missleading names')

        if broker == None:
            broker=os.getenv("AMQP_BROKER", "localhost")

        if exchange == None:
            exchange=os.getenv("AMQP_INPUT_EXCHANGE", "amq.topic")

        if exchange_type == None:
            exchange_type=os.getenv("AMQP_INPUT_EXCHANGE_TYPE", "topic")

        if queue == None:
            queue=os.getenv("AMQP_INPUT_QUEUE", "default")

        if routing_key == None:
            routing_key=os.getenv("AMQP_INPUT_ROUTING_KEY", "default")

        self.broker = broker
        self.exchange = exchange
        self.exchange_type = exchange_type
        self.queue = queue
        self.routing_key=routing_key
        self.debug = debug

        self.auto_delete = auto_delete
        self.exclusive = exclusive
        self.durable = durable

        self.connection = None
        self.channel = None
        self.connect()

        setup_sub()


    def consume(self, cb):
        if self.debug:
            sys.stdout.write("DEBUG: Consumer: received rabbit message\n")
            sys.stdout.flush()
        self.cb = cb
        
        retry_count = 0
        # This is a retry loop, on times when we get disconnected we should reconnect
        while retry_count < 5:
            # setup the consumer
            self.channel.basic_qos(prefetch_size=0, prefetch_count=500)
            self.channel.basic_consume(self.consume_cb, queue=self.queue, no_ack=False)
            try:
                # consume messages
                if self.debug:
                    sys.stdout.write("DEBUG: Consumer: consuming\n")
                    sys.stdout.flush()
                self.channel.start_consuming()
            except pika.exceptions.AMQPChannelError as err:
                print("Consumer: Caught a channel error: {}, reconnecting...".format(err))
                sys.stdout.flush()
                self.connect()
                retry_count += 1
                continue
            except pika.exceptions.AMQPConnectionError:
                print("Consumer: Connection was closed, reconnecting...")
                sys.stdout.flush()
                self.connect()
                retry_count += 1
                continue
        if retry_count == 5:
            raise RuntimeError('consumer reconnect failed after 5 attempts')

    def consume_cb(self, ch, method, properties, body):
        if self.debug:
            sys.stdout.write("DEBUG: Consumer: acking\n")
            sys.stdout.flush()
        ch.basic_ack(delivery_tag=method.delivery_tag)
        if self.debug:
            sys.stdout.write("DEBUG: Consumer: calling callback\n")
            sys.stdout.flush()
        self.cb(body)
        if self.debug:
            sys.stdout.write("DEBUG: Consumer: callback complete\n")
            sys.stdout.flush()
        received_counter.labels(analytic=analytic_name, exchange=self.exchange, queue=self.queue, type="amqp").inc()
        if self.debug:
            sys.stdout.write("DEBUG: Consumer: metric complete\n")
            sys.stdout.flush()

    def connect(self):
        if self.debug:
            sys.stdout.write("DEBUG: Consumer: connecting\n")
            sys.stdout.flush()

        self.close()

        conn = pika.BlockingConnection(pika.ConnectionParameters(self.broker))
        self.connection = conn
        self.channel = self.connection.channel()

        self.channel.exchange_declare(exchange=self.exchange,
                                      exchange_type=self.exchange_type,
                                      durable=True)
        self.channel.queue_declare(queue=self.queue,
                                   auto_delete=self.auto_delete,
                                   exclusive=self.exclusive,
                                   durable=self.durable)
        self.channel.queue_bind(exchange=self.exchange, queue=self.queue,
                                routing_key=self.routing_key)

        if self.debug:
            sys.stdout.write("DEBUG: Consumer: connected\n")
            sys.stdout.flush()

    def close(self):

        if self.channel != None:
            try:
                self.channel.close()
            except Exception as e:
                pass
            self.channel = None

        if self.connection != None:
            try:
                self.connection.close()
            except Exception as e:
                pass
            self.connection = None

class Publisher:
    def __init__(self, broker=None, routing_key=None, exchange=None, exchange_type=None):

        if not analytic_configured:
            print('ERROR - analytic module has not been configured, some metrics may have missleading names')

        if broker == None:
            broker=os.getenv("AMQP_BROKER", "localhost")

        if exchange == None:
            exchange=os.getenv("AMQP_OUTPUT_EXCHANGE", "amq.topic")

        if exchange_type == None:
            exchange_type=os.getenv("AMQP_OUTPUT_EXCHANGE_TYPE", "topic")
        
        if routing_key == None:
            routing_key=os.getenv("AMQP_OUTPUT_ROUTING_KEY", "default")

        self.broker = broker
        self.exchange = exchange
        self.routing_key = routing_key
        self.exchange_type = exchange_type

        self.connection = None
        self.channel = None
        self.connect()

        setup_pub()


    def publish(self, body, routing_key=None):

        if routing_key==None:
            routing_key = self.routing_key
        
        retry_count = 0
        while retry_count < 3:
            try:
                self.channel.basic_publish(exchange=self.exchange,
                                           routing_key=routing_key,
                                           body=body,
                                           properties=pika.BasicProperties(
                                               headers={'timestamp_in_ns': "%.0f" % (time.time()*1000000000) } # Add a time in ns
                                           ))
                sent_counter.labels(analytic=analytic_name, exchange=self.exchange, routing_key=routing_key, type="amqp").inc()
                break
            except pika.exceptions.AMQPChannelError as err:
                print("Publisher: Caught a channel error: {}, reconnecting...".format(err))
                self.connect()
                retry_count += 1
                continue
            except pika.exceptions.AMQPConnectionError:
                print("Publisher: Connection was closed, reconnecting...")
                self.connect()
                retry_count += 1
                continue

        if retry_count == 3:
            raise RuntimeError('publisher connect failed after 3 attempts')

    def connect(self):

        self.close()
        conn = pika.BlockingConnection(pika.ConnectionParameters(self.broker))
        self.connection = conn
        self.channel = self.connection.channel()
        
        self.channel.exchange_declare(exchange=self.exchange,
                                              exchange_type=self.exchange_type,
                                              durable=True)

    def close(self):

        if self.channel != None:
            try:
                self.channel.close()
            except Exception as e:
                pass
            self.channel = None
                      
        if self.connection != None:
            try:
                self.connection.close()
            except Exception as e:
                pass
            self.Connection = None
