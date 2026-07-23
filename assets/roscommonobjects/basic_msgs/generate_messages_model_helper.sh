#!/bin/bash
package_list=$@

function parserToRosModel(){    
    msg_desc=""
    for word in $1; do
        word="$(echo $word | sed -e 's/\[[^][]*\]/[]/g' )"
        if [[ $word == *"/"* ]]; then
            ref="${word//\//\/msg\/}"
            if [[ $ref = *"[]"* ]]; then
                msg_desc+='"'${ref%"[]"}'"[]'
            else
                msg_desc+='"'$ref'"'
            fi
        else
            msg_desc+=" "$word" "
        fi
    done
    echo $msg_desc
}

for p in $package_list
do
    specs_fullname=$(ros2 interface package $p)
    arr_specs=()
    arr_msgs=()
    arr_srvs=()

    echo $p':'

    for i in $specs_fullname
    do
      if [[ "$i" == *"/msg"* ]]; then
        arr_msgs="$arr_msgs $i"
      fi
      if [[ "$i" == *"/srv"* ]]; then
        arr_srvs="$arr_srvs $i"
      fi
    done
    if [[ ${#arr_msgs[@]} > 0 ]]; then
      echo "  msgs:"
      for i in $arr_msgs
      do
        message=${i/$p\/msg\//}
        #message_show="$(ros2 interface show $i)"
        #message_show=$(ros2 interface show $i | grep -v '	' | grep -v '^#' )
        #message_show=$(echo -e $message_show | sed -e 's/\s=\s/=/g')
        #final_desc=$(parserToRosModel "$message_show")
        echo '    '$message
        echo '      message'
        while read -r line
        do
          echo "       $(parserToRosModel "$line")"
        done < <(ros2 interface show $i | grep -v '	' | sed -e 's/\s=\s/=/g')
      done
    fi

    if [[ ${#arr_srvs[@]} > 0 ]]; then
      echo "  srvs:"
      for i in $arr_srvs
      do
        service=${i/$p\/srv\//}
        #service_show=$(ros2 interface show $i | grep -v '	' | grep -v '^#' )
        #request="$(echo $service_show | sed 's/---.*//' | sed -e 's/\s=\s/=/g')"
        #response="$(echo $service_show | sed -e 's#.*---\(\)#\1#'| sed -e 's/\s=\s/=/g')"
        #final_request=$(parserToRosModel "$request")
        #final_response=$(parserToRosModel "$response")   
        echo '    '$service
        echo '      request'
        while read -r line
        do
          echo "        $(parserToRosModel "$line")"
        done < <(ros2 interface show $i | grep -v '	' | grep -v '^#'| sed 's/---.*//' | sed -e 's/\s=\s/=/g')
        echo '      response'
        while read -r line
        do
          echo "        $(parserToRosModel "$line")"
        done < <(ros2 interface show $i | grep -v '	' | grep -v '^#'| sed -e 's#.*---\(\)#\1#'| sed -e 's/\s=\s/=/g')
      done
    fi

done