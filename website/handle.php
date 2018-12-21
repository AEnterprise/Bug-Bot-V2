<?php
// $method = "POST";
// $url = "http://84.55.63.20:8080/BugBot/reports";
$asd = $_POST;
// $data = json_encode($data);

$service_url = 'http://54.36.108.140:8080/BugBot/reports';
$curl = curl_init($service_url);
// $curl_post_data = json_encode(array(
//         'title' => $_POST['title'],
//         'steps' => $_POST['steps'],
//         'expected' => $_POST['expected'],
//         'actual' => $_POST['actual'],
//         'client_info' => $_POST['client_info'],
//         'device_info' => $_POST['device_info'],
//         'platform' => $_POST['platform'],
//         'user_id' => $_POST['user_id']
// ));
$curl_post_data = json_encode($_POST);
curl_setopt($curl, CURLOPT_RETURNTRANSFER, true);
curl_setopt($curl, CURLOPT_POST, true);
curl_setopt($curl, CURLOPT_POSTFIELDS, $curl_post_data);
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
if (isset($decoded->response->status) && $decoded->response->status == 'ERROR') {
    die('error occured: ' . $decoded->response->errormessage);
}
echo 'response ok!';
var_export($decoded->response);
?>