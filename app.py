from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
import mysql.connector
import os

# Configurar Flask
app = Flask(__name__)
app.secret_key = 'tu_clave_secreta_aqui'

# Configurar carpeta de imágenes
UPLOAD_FOLDER = os.path.join('static', 'img')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

# Función para validar extensiones
def extension_valida(nombre):
    return '.' in nombre and nombre.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Conexión a MySQL
conexion = mysql.connector.connect(
    host='localhost',
    user='root',
    password='Chapo4f4.',
    database='cafe_rapida'
)

# Página principal
@app.route('/')
def index():
    return render_template('index.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form['usuario']
        password = request.form['password']
        session['usuario'] = usuario
        if usuario == 'cafeteria':
            return redirect(url_for('panel'))
        else:
            return redirect(url_for('menu'))
    return render_template('login.html')

# Menú de comidas
@app.route('/menu')
def menu():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT * FROM productos ORDER BY categoria")
    productos = cursor.fetchall()
    cursor.close()
    return render_template('menu.html', productos=productos, usuario=session['usuario'])

# Logout
@app.route('/logout')
def logout():
    session.pop('usuario', None)
    return redirect(url_for('index'))

# Panel de control
@app.route('/panel')
def panel():
    if 'usuario' not in session or session['usuario'] != 'cafeteria':
        return redirect(url_for('login'))

    cursor = conexion.cursor(dictionary=True)
    cursor.execute("SELECT * FROM productos ORDER BY categoria")
    productos = cursor.fetchall()
    cursor.close()
    return render_template('panel.html', productos=productos)

# Agregar productos (solo para cafeteria)
@app.route('/agregar', methods=['GET', 'POST'])
def agregar():
    if 'usuario' not in session or session['usuario'] != 'cafeteria':
        return redirect(url_for('login'))

    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = request.form['precio']
        unidades = request.form['unidades']
        categoria = request.form['categoria']

        imagen = request.files['imagen']
        if imagen and extension_valida(imagen.filename):
            filename = secure_filename(imagen.filename)
            ruta = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            imagen.save(ruta)
            ruta_final = f'img/{filename}'
        else:
            ruta_final = 'img/default.jpg'

        cursor = conexion.cursor()
        cursor.execute("INSERT INTO productos (nombre, descripcion, precio, unidades, categoria, imagen) VALUES (%s, %s, %s, %s, %s, %s)",
                       (nombre, descripcion, precio, unidades, categoria, ruta_final))
        conexion.commit()
        cursor.close()
        return redirect(url_for('panel'))

    return render_template('agregar.html')

# Editar productos
@app.route('/editar/<int:id>', methods=['GET', 'POST'])
def editar(id):
    if 'usuario' not in session or session['usuario'] != 'cafeteria':
        return redirect(url_for('login'))

    cursor = conexion.cursor(dictionary=True)  # <- aquí está el cambio importante

    if request.method == 'POST':
        nombre = request.form['nombre']
        descripcion = request.form['descripcion']
        precio = request.form['precio']
        unidades = request.form['unidades']
        categoria = request.form['categoria']

        imagen = request.files['imagen']
        if imagen and extension_valida(imagen.filename):
            filename = secure_filename(imagen.filename)
            ruta = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            imagen.save(ruta)
            ruta_final = f'img/{filename}'
            cursor.execute("""UPDATE productos SET nombre=%s, descripcion=%s, precio=%s, unidades=%s, categoria=%s, imagen=%s WHERE id=%s""",
                           (nombre, descripcion, precio, unidades, categoria, ruta_final, id))
        else:
            cursor.execute("""UPDATE productos SET nombre=%s, descripcion=%s, precio=%s, unidades=%s, categoria=%s WHERE id=%s""",
                           (nombre, descripcion, precio, unidades, categoria, id))

        conexion.commit()
        cursor.close()
        return redirect(url_for('panel'))

    cursor.execute("SELECT * FROM productos WHERE id = %s", (id,))
    producto = cursor.fetchone()
    cursor.close()
    return render_template('editar.html', producto=producto)

# Eliminar productos
@app.route('/eliminar/<int:id>', methods=['POST'])
def eliminar(id):
    if 'usuario' not in session or session['usuario'] != 'cafeteria':
        return redirect(url_for('login'))

    cursor = conexion.cursor()
    cursor.execute("DELETE FROM productos WHERE id = %s", (id,))
    conexion.commit()   
    cursor.close()
    return redirect(url_for('panel'))

# Inicializar carrito si no existe
def obtener_carrito():
    if 'carrito' not in session:
        session['carrito'] = []
    return session['carrito']

# Agregar producto al carrito
@app.route('/agregar_al_carrito/<int:producto_id>')
def agregar_al_carrito(producto_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    carrito = obtener_carrito()
    for item in carrito:
        if item['id'] == producto_id:
            item['cantidad'] += 1
            break
    else:
        cursor = conexion.cursor(dictionary=True)
        cursor.execute("SELECT * FROM productos WHERE id = %s", (producto_id,))
        producto = cursor.fetchone()
        cursor.close()
        if producto:
            carrito.append({
                    'id': producto['id'],
                    'nombre': producto['nombre'],
                    'precio': float(producto['precio']),
                    'cantidad': 1,
                    'imagen': producto['imagen']
                })


    session['carrito'] = carrito
    return redirect(url_for('menu'))

# Ver carrito
@app.route('/carrito')
def carrito():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    carrito = obtener_carrito()
    total = sum(item['precio'] * item['cantidad'] for item in carrito)
    
    # Aquí añadimos productos=carrito para que {% if productos %} funcione
    return render_template('carrito.html', carrito=carrito, total=total, productos=carrito)


# Eliminar producto del carrito
@app.route('/eliminar_del_carrito/<int:producto_id>')
def eliminar_del_carrito(producto_id):
    if 'usuario' not in session:
        return redirect(url_for('login'))

    carrito = obtener_carrito()
    carrito = [item for item in carrito if item['id'] != producto_id]
    session['carrito'] = carrito
    return redirect(url_for('carrito'))

# Vaciar carrito
@app.route('/vaciar_carrito', methods=['POST'])
def vaciar_carrito():
    if 'usuario' not in session:
        return redirect(url_for('login'))
    session['carrito'] = []
    return redirect(url_for('carrito'))

# Realizar pedido (por ahora solo limpia el carrito y da mensaje)
@app.route('/realizar_pedido', methods=['POST'])
def realizar_pedido():
    if 'usuario' not in session:
        return redirect(url_for('login'))

    # Aquí puedes guardar el pedido en la base de datos si lo deseas

    session.pop('carrito', None)
    return render_template('pedido_exito.html')

# Ejecutar app
if __name__ == '__main__':
    app.run(debug=True)
