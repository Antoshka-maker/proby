<?php
// Только для проверки на своём компьютере: php -S localhost:8000 router-dev.php
$p = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
if (preg_match('~^/(content|data|cache|inc)(/|$)|^/config\.php~', $p)) { http_response_code(403); exit; }
if ($p !== '/' && is_file(__DIR__ . $p)) return false;
require __DIR__ . '/index.php';
