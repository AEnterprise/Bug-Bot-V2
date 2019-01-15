<?php
$asd = $_POST;
$configs = include('config.php');
$service_url = $configs->webserver_url;
$curl = curl_init($service_url);
$curl_post_data = json_encode($_POST);
print_r($_POST);
print("<br/>");
curl_setopt($curl, CURLOPT_RETURNTRANSFER, true);
curl_setopt($curl, CURLOPT_POST, true);
curl_setopt($curl, CURLOPT_POSTFIELDS, $_POST);
$curl_response = curl_exec($curl);
if ($curl_response === false) {
    $info = curl_getinfo($curl);
    curl_close($curl);
    echo "ASD";
    var_dump($curl_post_data);
    die('error occured during curl exec. Additioanl info: ' . var_export($info));
}
curl_close($curl);
$decoded = json_decode($curl_response);
print("Response: ");
print_r($curl_response);
print("<br/>");
echo 'response ok!';
?>