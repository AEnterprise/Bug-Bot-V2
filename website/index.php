<?php
            $configs = include('config.php');
            ini_set('display_errors', 1);
            ini_set('display_startup_errors', 1);
            error_reporting(E_ALL);
            if (isset($_GET["error"])) {
                echo json_encode(array("message" => "Authorization Error"));
            } elseif (isset($_GET["code"])) {
                Header("Location: login.php?code={$_GET["code"]}");
            } else {
                Header("Location: https://discordapp.com/oauth2/authorize?client_id=".$configs->client_id."&response_type=code&scope=identify");
            }
?>
<!DOCTYPE html>
    <html lang="en">
      <head>
        <title>Bug Report Tool</title>
        <meta charset="utf-8" />
        <meta property="og:url" content="https://dabbit.typeform.com/to/mnlaDU" />
        <meta property="og:title" content="Bug Report Tool" />
        <meta property="og:type" content="website" />
        <meta
          name="viewport"
          content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover"
        />

    <style>
      html,
      body{
        background-color: rgb(44, 47, 51);
      }
      .myButton {
        background-color:#01b7db;
        -moz-border-radius:8px;
        -webkit-border-radius:8px;
        border-radius:8px;
        border:1px solid #01b7db;
        display:inline-block;
        cursor:pointer;
        color:#ffffff;
        font-family:Arial;
        font-size:18px;
        font-weight: bold;
        padding:16px 31px;
        text-decoration:none;
        text-shadow:0px 1px 0px #01b7db;
      }
      .myButton:hover {
        background-color:#01b7db;
      }
      .myButton:active {
        position:relative;
        top:1px;
      }
    </style>
  </head>
  <body>
        <div class="logo"><center><img src="./img/default.png"></center></div>

        <div>
          <center><h3 style="color: white; width: 60%; font-size: 24px;">This tool is for generating text for Bug-Bot's !submit command in a less confusing fashion. You cannot submit a bug directly through this form. Any feedback regarding it can be sent to Dabbit Prime.</h3></center>
        </div>

        <div>
           <center><a href="./submit.php" class="myButton">Let's get started</a></center>
        </div>
  </body>
</html>
<!-- https://dabbit.typeform.com/to/mnlaDU -->