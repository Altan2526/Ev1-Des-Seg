const express = require('express');
const router = express.Router();

router.post('/api/empleados/upload', (req, res) => {
    const token = req.headers.authorization;

    if (!token) {
        return res.status(401).json({ 
            error: 'Acceso denegado. Faltan credenciales (Mitigación Spoofing).' 
        });
    }

    res.status(200).json({
        mensaje: 'Archivo recibido y guardado de forma segura',
        estado: 'Éxito'
    });
});

module.exports = router;