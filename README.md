# Spy boy v.0.1.2
Usually calls himself "Simple log bot" to stay undercover. Spy boy is a bot that looks form behind a corner to
text channels of your interests and writes down everything he sees to the other channel. Rumors say that in future 
he will be trained to perform some special missions such as spying a single person on the server.

# Installation

To hire the Spy boy you need to visit nearest restaurant that serves Chinese mini-tacos. Then, bill the waiter with
10 bucks. Then proceed quickly to the phone box on the other side of the street. Phone will be already calling. The
secret password is "hajduszoboszlo". Explain your need of Spy Boy to the man and you will find it on your server when
you are back home.

Or just click the link below and follow the instructions. It's probably easier.
 
https://discordapp.com/api/oauth2/authorize?client_id=624905494011707413&permissions=125952&scope=bot

# Usage

There are several of the missions you can send the Spy Boy to. All of the available for now are listed below

1. **Spy**   
It should be obvious that a spy can... spy. You can send Spy Boy to observe some channels and copy all of the messages
sent to the other channel. This way nothing will be lost for your eyes if you want to clean some uncomfortable
information later...   
To send the Spy Boy on the spy mission just type:

       %spy <channel_name_to_spy> <channel_name_to_send_messages_to>
   
   Don't forget to replace '<>' blocks with proper channel names. They are pretty
   self-explanatory. Proper command that sends messages from channel `offtop` to 
   channel `admin-channel-1` could look like that:
   
       %spy offtop admin-channel-1
       
   It's recommended to have a different log channel for each spied channel. It would be a 
   disaster if messages from two different channels were mixed up in one place. To help you avoid this
   there is a command that lists all of your bot's spy missions. Just say:
   
       %spy_list
       
   But if you **still** manage to mess up your info destination, you can change it by invoking
   the `spy` command again with the same <channel_name_to_spy>. For example if you want to change
   `offtop` destination from `admin-channel-1` to `pineapple`, type:
   
       %spy offtop pineapple
       
    And your archive will be saved! 
       
   **But how do I order Spy boy to stop spying this poor people?**   
   Don't you worry. If you think that you have enough information stored, you can use
   `spy_stop` command to increase the privacy of your people again. Type:
       
       %spy_stop <channel_name_to_stop_spying>
       
   Example:
   
       %spy_stop offtop
       
   Would make `offtop` free from spying again.

1. **Cleaning**   
Sometimes there are information that shouldn't be seen by mortals' eyes for too long. You can
order the Spy boy to delete the messages on chosen channel from time to time. There is a command
for this:

       %cleaning <channel_name> <message_expire_time> <cleaning_interval>
       
   Okay, these surely are not so self-explanatory. Let's get through them one by one:
   * **channel_name**   
   This one is simple. It's the channel name on which you want to set up cleaning.
   * **message_expire_time**   
   This monsieur is a bit special because it needs to be passed in this format:
        
         <days>:<hours>:<minutes>:<seconds>
         
     This indicated how old the message needs to be to classify it for deletion. It's the
     easiest to explain on an example:
     
         1:12:5:12
         
     This will delete all of the messages that are older than 1 day, 12 hours, 5 minutes and
     12 second. Summed up of course.
     
         0:0:10
         
     This one deletes messages older than 10 minutes. As you can see, you can omit zeros on
     the right, but you cannot from the left. If you type just this:
     
         10
         
      You will end up with expire time set on 10 days.
      
    * **cleaning_interval**   
    This changes how often the channel will be searched by bot for expired messages to delete.
    Format of this one is the same as the format of <message_expire_time>.
    
   Now an example to sum it up:   
    
       %cleaning offtop 0:1 0:0:0:30
       
   After this command invoked, Spy boy will delete messages that are older than one day
   on `offtop` channel every 30 seconds until you tell him to stop. That's where
   `cleaning_stop` comes handy:
   
       %cleaning_stop <channel_name>
       
   As you can guess that command stops cleaning scheduled on target channel. If you ever forgot
   where did you set up your cleanings you can type:
   
       %cleaning_list
       
   
More functionalities coming soon!
