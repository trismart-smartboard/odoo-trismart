<?php

require_once ('vendor/autoload.php');
use OdooRPCClient\Client;


$data = [
    'host' => 'https://trismart-staging-15-0-3640780.dev.odoo.com',
    'database' => 'trismart-staging-15-0-3640780',
    'login' => 'admin',
    'password' => '0c5608e57939826227c64338c981070573de0700'
];
$odoo = new Client($data['host']);
$odoo->login($data['database'],$data['login'],$data['password']);

$sb_lead_id = 1;
$project_template_id = 1;

$new_project = $odoo->env['smartboard.connector']->create_project($sb_lead_id , $project_template_id);
var_dump($new_project);

?>
