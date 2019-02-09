<?php 
  $id = filter_input(INPUT_GET,"user",FILTER_SANITIZE_STRING);

?>
<!DOCTYPE html>
    <html lang="en">
      <head>
        <title>Bug Report Tool</title>
        <meta charset="utf-8" />
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
        color: white;
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
       <div>
          <center><h3 style="color: white; width: 80%; font-size: 24px;">Before submitting a bug, please make sure that you've checked<br> the relevant Trello boards to make sure your issue hasn't already been reported.<br>
          Desktop: https://trello.com/b/AExxR9lU/canary-bugs<br>
      Android: https://trello.com/b/Vqrkz3KO/android-beta-bugs<br>
      iOS: https://trello.com/b/vLPlnX60/ios-testflight-bugs<br>
      Linux: https://trello.com/b/UyU76Esh/linux-bugs<br>

      Another solution is to use the search command in the relevant reporting channel in the Discord Testers server</h3></center>
        </div>
        <div>
          <center><p style="color: white; width: 80%; font-size: 24px;">This tool will NOT submit a bug for you. It's intended use is to help you properly format text that Bug-Bot will accept in a reporting channel. Unfortunately, text from this website cannot be copied on mobile. I'm sorry but it's out of my control.</p></center>
        </div>
        <br>
        <br>
        <div style="display: inline;">
        	<center><h2><a id="edit" href="edit" style="color: white;">Edit Bug</a></h2> <h2><a href="bugs" style="color: white;">All bugs</a></h2></center>
        </div>
        <div>
          <center><form action="./handle.php" method="POST">
            <label name="title" >In a single sentence, describe your bug like you're telling a friend about it.</label><br>
            <textarea type="text" name="title"></textarea><br>
            <label name="steps" >What steps do you need to take to make this bug happen? </label><br>
            <textarea type="text" name="steps"></textarea><br>
            <label name="expected" >What is supposed to happen? *</label><br>
            <textarea type="text" name="expected"></textarea><br>
            <label name="actual" >What actually happens when you follow the steps you wrote earlier? *</label><br>
            <textarea type="text" name="actual"></textarea><br>
            <label name="client_info" >What build of Discord are you using? *</label><br>
            <textarea type="text" name="client_info"></textarea><br>
            <label name="device_info" >What device you are using? *</label><br>
            <textarea type="text" name="device_info"></textarea><br><br>
            <label name="platform" >What platform are you using? *</label><br>
              <select name="platform">
                  <option value="android">android</option>
                  <option value="ios">ios</option>
                  <option value="desktop">desktop</option>
                  <option value="linux">linux</option>
                  <option value="store">store</option>
                  <option value="marketing">marketing</option>
              </select>
            <input name="user_id" type="hidden" value="<?=$id?>">
              <br/>
              <br/>
              <br/>
            <button type="submit" class="myButton">Submit!</button>
          </form></center>  
        </div>
	  <script type="text/javascript">
	  	document.getElementById("edit").addEventListener("click", function(event){
		  event.preventDefault()
		  var bugid = prompt("Please enter Bug ID", "");
    window.location.replace("./edit.php?bug=" + bugid + "&user=<?=$id?>");

		});
	  </script>
  </body>
</html>
<!-- https://dabbit.typeform.com/to/mnlaDU -->
