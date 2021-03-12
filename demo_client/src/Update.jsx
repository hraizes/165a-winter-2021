import styled from 'styled-components';
import React, { useState } from 'react';

function Update(props) {
  const [primarykey,setprimarykey] = useState(null);
  const [col2,setcol2] = useState(null);
  const [col3,setcol3] = useState(null);
  const [col4,setcol4] = useState(null);
  const [col5,setcol5] = useState(null);
  return (
      <UpdateDisplay>
        <label>primary key: </label>
        <input onChange={(evt)=>{setprimarykey(evt.target.value)}} value={primarykey} ></input>
        <br/>
        <div>new values (blank to keep them the same): </div>
        <label> col2: </label>
        <UpdateInput  onChange={(evt)=>{setcol2(evt.target.value)}} value={col2} ></UpdateInput>
        <label> col3: </label>
        <UpdateInput  onChange={(evt)=>{setcol3(evt.target.value)}} value={col3} ></UpdateInput>
        <label> col4: </label>
        <UpdateInput  onChange={(evt)=>{setcol4(evt.target.value)}} value={col4} ></UpdateInput>
        <label> col5: </label>
        <UpdateInput  onChange={(evt)=>{setcol5(evt.target.value)}} value={col5} ></UpdateInput>
        <br/>
        <SubmitButton  onClick={()=>{props.appendTX({
          type:'update',
          primarykey,
          col2,
          col3,
          col4,
          col5
        })}}>
        add to transaction
        </SubmitButton>
      </UpdateDisplay>
  );
}

const UpdateInput = styled.input`
width:20px;
`;


const UpdateDisplay = styled.div`
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

export default Update;
