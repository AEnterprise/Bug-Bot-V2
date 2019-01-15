<?php
    $configs = include('config.php');

    ini_set('display_errors', 1);
    ini_set('display_startup_errors', 1);
    error_reporting(E_ALL);
    if (isset($_GET["error"])) {
        echo json_encode(array("message" => "Authorization Error"));
    } elseif (isset($_GET["code"])) {
        $redirect_uri = $configs->redirect_uri;
        $token_request = "https://discordapp.com/api/oauth2/token";
        $token = curl_init();
        curl_setopt_array($token, array(
            CURLOPT_URL => $token_request,
            CURLOPT_POST => 1,
            CURLOPT_POSTFIELDS => array(
                "grant_type" => "authorization_code",
                "client_id" => $configs->client_id,
                "client_secret" => $configs->client_secret,
                "redirect_uri" => $redirect_uri,
                "code" => $_GET["code"]
            )
        ));
        curl_setopt($token, CURLOPT_RETURNTRANSFER, true);
        $resp = json_decode(curl_exec($token));
        curl_close($token);
        if (isset($resp->access_token)) {
            $access_token = $resp->access_token;
            $info_request = "https://discordapp.com/api/users/@me";
            $info = curl_init();
            curl_setopt_array($info, array(
                CURLOPT_URL => $info_request,
                CURLOPT_HTTPHEADER => array(
                    "Authorization: Bearer {$access_token}"
                ),
                CURLOPT_RETURNTRANSFER => true
            ));
            $user = json_decode(curl_exec($info));
            curl_close($info);
            
            
            //get servers
            $access_token = $resp->access_token;
            $info_request = "https://discordapp.com/api/users/@me/guilds";
            $info = curl_init();
            curl_setopt_array($info, array(
                CURLOPT_URL => $info_request,
                CURLOPT_HTTPHEADER => array(
                    "Authorization: Bearer {$access_token}"
                ),
                CURLOPT_RETURNTRANSFER => true
            ));
            $data = json_decode(curl_exec($info));
            $found = false;
            foreach($data as $guild) {
                if ($guild-> id == "258274103935369219") {
                    $found = true;
                    break;
                }
            }
            
            if ($found)
                header("Location: submit.php?user={$user->id}");
            else
                header("HTTP/1.1 401 Unauthorized");
            
            
            
            
            //echo "<h1>Hello, {$user->username}#{$user->discriminator}.</h1><br><h2>{$user->id}</h2><br><img src='https://discordapp.com/api/v6/users/{$user->id}/avatars/{$user->avatar}.jpg' /><br><br>Dashboard Token: {$access_token}";
            
            //print_r($data);
        } else {
            echo json_encode(array("message" => "Authentication Error"));
        }
    } else {
        Header("Location: https://discordapp.com/oauth2/authorize?client_id=".$configs->client_id."&response_type=code&scope=identify");
    }
?>