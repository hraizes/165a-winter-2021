import styled from 'styled-components';
import React, { useState } from 'react';

function Insert(props) {
  const [col1,setcol1] = useState(null);
  const [col2,setcol2] = useState(null);
  const [col3,setcol3] = useState(null);
  const [col4,setcol4] = useState(null);
  const [col5,setcol5] = useState(null);
  return (
      <InsertDisplay>
        <label>col1(primary): </label>
        <InsertInput onChange={(evt)=>{setcol1(evt.target.value)}} value={col1} ></InsertInput>
        <label> col2: </label>
        <InsertInput  onChange={(evt)=>{setcol2(evt.target.value)}} value={col2} ></InsertInput>
        <label> col3: </label>
        <InsertInput  onChange={(evt)=>{setcol3(evt.target.value)}} value={col3} ></InsertInput>
        <label> col4: </label>
        <InsertInput  onChange={(evt)=>{setcol4(evt.target.value)}} value={col4} ></InsertInput>
        <label> col5: </label>
        <InsertInput  onChange={(evt)=>{setcol5(evt.target.value)}} value={col5} ></InsertInput>
        <br/>
        <SubmitButton onClick={()=>{props.appendTX({
          type:'insert',
          col1,
          col2,
          col3,
          col4,
          col5
        })}}>
        add to transaction
        </SubmitButton>
      </InsertDisplay>
  );
}

const InsertInput = styled.input`
width:20px;
`;

const InsertDisplay = styled.div`
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

export default Insert;
