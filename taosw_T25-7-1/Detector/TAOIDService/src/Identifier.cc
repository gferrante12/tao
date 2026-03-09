//
//  Author: Jiayang Xu  2023.1.10
//  E-mail:xujy@ihep.ac.cn
//
#include "TAOIDService/Identifier.h"
#include <stdarg.h>
#include <stdio.h>
#include <algorithm>

#include <iostream>
#include <iomanip>

//-----------------------------------------------
void Identifier::set (const std::string& id)
{
    sscanf (id.c_str(), "0x%lx", &m_id);
}


//-----------------------------------------------
std::string Identifier::getString() const
{
    std::string result;
    char temp[20];

    sprintf (temp, "0x%016lx", (uint64_t)m_id);
    //result += temp;
    //result.insert(2,10-result.length(),'0');
    //return (result);
    return std::string(temp);
}

//-----------------------------------------------
void Identifier::show () const
{
    const Identifier& me = *this;
    std::cout << me.getString();
}

//-----------------------------------------------
std::ostream& operator<<(std::ostream & os, const Identifier& Id)
{
    return (os<<Id.getString());
}