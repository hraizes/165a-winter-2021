import styled from 'styled-components';
import React, { useState } from 'react';

function Delete(props) {
  const [key,setKey] = useState(0);
  return (
      <DeleteDisplay>
        <label>primary key: </label>
        <input onChange={(evt)=>{setKey(evt.target.value)}} value={key}></input>
        <br/>
        <SubmitButton  onClick={()=>{props.appendTX({
          type:'delete',
          key
        })}}>
        add to transaction
        </SubmitButton>
      </DeleteDisplay>
  );
}


const DeleteDisplay = styled.div`
box-shadow:0 30px 50px -30px rgba(0,0,0,.15);
background-color:#fff;
padding:10px;
height:120px;
`;

const SubmitButton = styled.button`
background-color:#0cce6b;
color:'white';
margin:30px 10px 10px 0px;
border:none;
border-radius:4px;
padding:5px;
font-size:15px;

transition:border-color 0.2s, color 0.2s, background-color 0.2s;

:hover{
  background-color:#dbdbdb;
  color:black;
  border-color:#dbdbdb;
}
`;

export default Delete;
