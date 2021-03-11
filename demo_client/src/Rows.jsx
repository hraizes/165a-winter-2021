import styled from 'styled-components';
import React, { useState } from 'react';

function Rows(props) {
  return (
      <RowDisplay>
        {
            props.rows.map((row)=>{
                return <div>
                    {row.map((col)=>{
                        return <span>{col}</span>
                    })}
                </div>
            })
        }
      </RowDisplay>
  );
}


const RowDisplay = styled.div`
box-shadow:0 30px 50px -30px rgba(0,0,0,.15);
background-color:#fff;
padding:20px;
height:200px;
overflow-y:scroll;
`;

export default Rows;
