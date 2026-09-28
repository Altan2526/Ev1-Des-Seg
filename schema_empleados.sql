CREATE TABLE empleados (
    id INT AUTO_INCREMENT PRIMARY KEY,
    rut VARCHAR(12) UNIQUE NOT NULL,
    nombre_completo VARCHAR(100) NOT NULL,
    cargo VARCHAR(50) NOT NULL,
    centro_costo VARCHAR(50),
    fecha_ingreso DATE NOT NULL
);

CREATE TABLE cargas_familiares (
    id INT AUTO_INCREMENT PRIMARY KEY,
    empleado_id INT,
    rut_carga VARCHAR(12) UNIQUE NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    parentesco VARCHAR(30),
    FOREIGN KEY (empleado_id) REFERENCES empleados(id)
);