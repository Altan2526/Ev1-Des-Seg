import React, { useState } from 'react';

export default function FormularioEmpleado() {
    const [datos, setDatos] = useState({ rut: '', nombre: '' });

    const manejarCambio = (e) => {
        // Sanitización básica: bloquea inyección de scripts HTML (Mitigación Tampering)
        const valorSeguro = e.target.value.replace(/[<>]/g, "");
        setDatos({ ...datos, [e.target.name]: valorSeguro });
    };

    return (
        <form className="formulario-seguro">
            <h2>Ingreso Ficha del Personal</h2>
            
            <label>RUT del Empleado:</label>
            <input type="text" name="rut" onChange={manejarCambio} required />

            <label>Nombre Completo:</label>
            <input type="text" name="nombre" onChange={manejarCambio} required />

            <button type="submit">Guardar Ficha</button>
        </form>
    );
}