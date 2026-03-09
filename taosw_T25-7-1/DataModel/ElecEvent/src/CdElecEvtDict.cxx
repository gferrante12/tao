// Do NOT change. Changes will be lost next time file is generated

#define R__DICTIONARY_FILENAME dItmpdIbdIjunodOihepdOacdOcndIel9_amd64_gcc11dIReleasedIJ25dO7dO1dItaoswdIbuilddIDataModeldIElecEventdIsrcdICdElecEvtDict
#define R__NO_DEPRECATION

/*******************************************************************/
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#define G__DICTIONARY
#include "ROOT/RConfig.hxx"
#include "TClass.h"
#include "TDictAttributeMap.h"
#include "TInterpreter.h"
#include "TROOT.h"
#include "TBuffer.h"
#include "TMemberInspector.h"
#include "TInterpreter.h"
#include "TVirtualMutex.h"
#include "TError.h"

#ifndef G__ROOT
#define G__ROOT
#endif

#include "RtypesImp.h"
#include "TIsAProxy.h"
#include "TFileMergeInfo.h"
#include <algorithm>
#include "TCollectionProxyInfo.h"
/*******************************************************************/

#include "TDataMember.h"

// Header files passed as explicit arguments
#include "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/ElecEvent/Event/CdElecEvt.h"

// Header files passed via #pragma extra_include

// The generated code does not explicitly qualify STL entities
namespace std {} using namespace std;

namespace ROOT {
   static void *new_TaocLcLCdElecEvt(void *p = nullptr);
   static void *newArray_TaocLcLCdElecEvt(Long_t size, void *p);
   static void delete_TaocLcLCdElecEvt(void *p);
   static void deleteArray_TaocLcLCdElecEvt(void *p);
   static void destruct_TaocLcLCdElecEvt(void *p);

   // Function generating the singleton type initializer
   static TGenericClassInfo *GenerateInitInstanceLocal(const ::Tao::CdElecEvt*)
   {
      ::Tao::CdElecEvt *ptr = nullptr;
      static ::TVirtualIsAProxy* isa_proxy = new ::TInstrumentedIsAProxy< ::Tao::CdElecEvt >(nullptr);
      static ::ROOT::TGenericClassInfo 
         instance("Tao::CdElecEvt", ::Tao::CdElecEvt::Class_Version(), "Event/CdElecEvt.h", 11,
                  typeid(::Tao::CdElecEvt), ::ROOT::Internal::DefineBehavior(ptr, ptr),
                  &::Tao::CdElecEvt::Dictionary, isa_proxy, 4,
                  sizeof(::Tao::CdElecEvt) );
      instance.SetNew(&new_TaocLcLCdElecEvt);
      instance.SetNewArray(&newArray_TaocLcLCdElecEvt);
      instance.SetDelete(&delete_TaocLcLCdElecEvt);
      instance.SetDeleteArray(&deleteArray_TaocLcLCdElecEvt);
      instance.SetDestructor(&destruct_TaocLcLCdElecEvt);
      return &instance;
   }
   TGenericClassInfo *GenerateInitInstance(const ::Tao::CdElecEvt*)
   {
      return GenerateInitInstanceLocal(static_cast<::Tao::CdElecEvt*>(nullptr));
   }
   // Static variable to force the class initialization
   static ::ROOT::TGenericClassInfo *_R__UNIQUE_DICT_(Init) = GenerateInitInstanceLocal(static_cast<const ::Tao::CdElecEvt*>(nullptr)); R__UseDummy(_R__UNIQUE_DICT_(Init));
} // end of namespace ROOT

namespace Tao {
//______________________________________________________________________________
atomic_TClass_ptr CdElecEvt::fgIsA(nullptr);  // static to hold class pointer

//______________________________________________________________________________
const char *CdElecEvt::Class_Name()
{
   return "Tao::CdElecEvt";
}

//______________________________________________________________________________
const char *CdElecEvt::ImplFileName()
{
   return ::ROOT::GenerateInitInstanceLocal((const ::Tao::CdElecEvt*)nullptr)->GetImplFileName();
}

//______________________________________________________________________________
int CdElecEvt::ImplFileLine()
{
   return ::ROOT::GenerateInitInstanceLocal((const ::Tao::CdElecEvt*)nullptr)->GetImplFileLine();
}

//______________________________________________________________________________
TClass *CdElecEvt::Dictionary()
{
   fgIsA = ::ROOT::GenerateInitInstanceLocal((const ::Tao::CdElecEvt*)nullptr)->GetClass();
   return fgIsA;
}

//______________________________________________________________________________
TClass *CdElecEvt::Class()
{
   if (!fgIsA.load()) { R__LOCKGUARD(gInterpreterMutex); fgIsA = ::ROOT::GenerateInitInstanceLocal((const ::Tao::CdElecEvt*)nullptr)->GetClass(); }
   return fgIsA;
}

} // namespace Tao
namespace Tao {
//______________________________________________________________________________
void CdElecEvt::Streamer(TBuffer &R__b)
{
   // Stream an object of class Tao::CdElecEvt.

   if (R__b.IsReading()) {
      R__b.ReadClassBuffer(Tao::CdElecEvt::Class(),this);
   } else {
      R__b.WriteClassBuffer(Tao::CdElecEvt::Class(),this);
   }
}

} // namespace Tao
namespace ROOT {
   // Wrappers around operator new
   static void *new_TaocLcLCdElecEvt(void *p) {
      return  p ? new(p) ::Tao::CdElecEvt : new ::Tao::CdElecEvt;
   }
   static void *newArray_TaocLcLCdElecEvt(Long_t nElements, void *p) {
      return p ? new(p) ::Tao::CdElecEvt[nElements] : new ::Tao::CdElecEvt[nElements];
   }
   // Wrapper around operator delete
   static void delete_TaocLcLCdElecEvt(void *p) {
      delete (static_cast<::Tao::CdElecEvt*>(p));
   }
   static void deleteArray_TaocLcLCdElecEvt(void *p) {
      delete [] (static_cast<::Tao::CdElecEvt*>(p));
   }
   static void destruct_TaocLcLCdElecEvt(void *p) {
      typedef ::Tao::CdElecEvt current_t;
      (static_cast<current_t*>(p))->~current_t();
   }
} // end of namespace ROOT for class ::Tao::CdElecEvt

namespace ROOT {
   static TClass *vectorlETaocLcLCdElecChannelgR_Dictionary();
   static void vectorlETaocLcLCdElecChannelgR_TClassManip(TClass*);
   static void *new_vectorlETaocLcLCdElecChannelgR(void *p = nullptr);
   static void *newArray_vectorlETaocLcLCdElecChannelgR(Long_t size, void *p);
   static void delete_vectorlETaocLcLCdElecChannelgR(void *p);
   static void deleteArray_vectorlETaocLcLCdElecChannelgR(void *p);
   static void destruct_vectorlETaocLcLCdElecChannelgR(void *p);

   // Function generating the singleton type initializer
   static TGenericClassInfo *GenerateInitInstanceLocal(const vector<Tao::CdElecChannel>*)
   {
      vector<Tao::CdElecChannel> *ptr = nullptr;
      static ::TVirtualIsAProxy* isa_proxy = new ::TIsAProxy(typeid(vector<Tao::CdElecChannel>));
      static ::ROOT::TGenericClassInfo 
         instance("vector<Tao::CdElecChannel>", -2, "vector", 389,
                  typeid(vector<Tao::CdElecChannel>), ::ROOT::Internal::DefineBehavior(ptr, ptr),
                  &vectorlETaocLcLCdElecChannelgR_Dictionary, isa_proxy, 0,
                  sizeof(vector<Tao::CdElecChannel>) );
      instance.SetNew(&new_vectorlETaocLcLCdElecChannelgR);
      instance.SetNewArray(&newArray_vectorlETaocLcLCdElecChannelgR);
      instance.SetDelete(&delete_vectorlETaocLcLCdElecChannelgR);
      instance.SetDeleteArray(&deleteArray_vectorlETaocLcLCdElecChannelgR);
      instance.SetDestructor(&destruct_vectorlETaocLcLCdElecChannelgR);
      instance.AdoptCollectionProxyInfo(TCollectionProxyInfo::Generate(TCollectionProxyInfo::Pushback< vector<Tao::CdElecChannel> >()));

      instance.AdoptAlternate(::ROOT::AddClassAlternate("vector<Tao::CdElecChannel>","std::vector<Tao::CdElecChannel, std::allocator<Tao::CdElecChannel> >"));
      return &instance;
   }
   // Static variable to force the class initialization
   static ::ROOT::TGenericClassInfo *_R__UNIQUE_DICT_(Init) = GenerateInitInstanceLocal(static_cast<const vector<Tao::CdElecChannel>*>(nullptr)); R__UseDummy(_R__UNIQUE_DICT_(Init));

   // Dictionary for non-ClassDef classes
   static TClass *vectorlETaocLcLCdElecChannelgR_Dictionary() {
      TClass* theClass =::ROOT::GenerateInitInstanceLocal(static_cast<const vector<Tao::CdElecChannel>*>(nullptr))->GetClass();
      vectorlETaocLcLCdElecChannelgR_TClassManip(theClass);
   return theClass;
   }

   static void vectorlETaocLcLCdElecChannelgR_TClassManip(TClass* ){
   }

} // end of namespace ROOT

namespace ROOT {
   // Wrappers around operator new
   static void *new_vectorlETaocLcLCdElecChannelgR(void *p) {
      return  p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<Tao::CdElecChannel> : new vector<Tao::CdElecChannel>;
   }
   static void *newArray_vectorlETaocLcLCdElecChannelgR(Long_t nElements, void *p) {
      return p ? ::new(static_cast<::ROOT::Internal::TOperatorNewHelper*>(p)) vector<Tao::CdElecChannel>[nElements] : new vector<Tao::CdElecChannel>[nElements];
   }
   // Wrapper around operator delete
   static void delete_vectorlETaocLcLCdElecChannelgR(void *p) {
      delete (static_cast<vector<Tao::CdElecChannel>*>(p));
   }
   static void deleteArray_vectorlETaocLcLCdElecChannelgR(void *p) {
      delete [] (static_cast<vector<Tao::CdElecChannel>*>(p));
   }
   static void destruct_vectorlETaocLcLCdElecChannelgR(void *p) {
      typedef vector<Tao::CdElecChannel> current_t;
      (static_cast<current_t*>(p))->~current_t();
   }
} // end of namespace ROOT for class vector<Tao::CdElecChannel>

namespace {
  void TriggerDictionaryInitialization_CdElecEvtDict_Impl() {
    static const char* headers[] = {
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/ElecEvent/Event/CdElecEvt.h",
nullptr
    };
    static const char* includePaths[] = {
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Python/3.11.10/include/python3.11",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Boost/1.85.0",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/log4cpp/1.1.3/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/ROOT/6.30.08/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/CLHEP/2.4.7.1/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J24.2.0/ExternalLibs/CLHEP/2.4.7.1/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/Geant4/10.04.p02.juno/include/geant4",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/HepMC/2.06.11/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/genie/3.04.02/include/GENIE",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/frontier/2.10.2/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/mysql-connector-c/6.1.9/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/mysql-connector-cpp/1.1.12/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libyaml/0.2.4/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libonnxruntime/1.17.3/include/onnxruntime",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/libonnxruntime/1.17.3/include/onnxruntime/core/session",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/ExternalLibs/nuwro/21.09.2/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/ElecEvent",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/ElecEvent/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/ElecEvent",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/junosw/InstallArea/include",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.4.0/ExternalLibs/ROOT/6.30.08/include/",
"/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/build/DataModel/ElecEvent/",
nullptr
    };
    static const char* fwdDeclCode = R"DICTFWDDCLS(
#line 1 "CdElecEvtDict dictionary forward declarations' payload"
#pragma clang diagnostic ignored "-Wkeyword-compat"
#pragma clang diagnostic ignored "-Wignored-attributes"
#pragma clang diagnostic ignored "-Wreturn-type-c-linkage"
extern int __Cling_AutoLoading_Map;
namespace Tao{class __attribute__((annotate("$clingAutoload$/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/ElecEvent/Event/CdElecEvt.h")))  CdElecEvt;}
)DICTFWDDCLS";
    static const char* payloadCode = R"DICTPAYLOAD(
#line 1 "CdElecEvtDict dictionary payload"


#define _BACKWARD_BACKWARD_WARNING_H
// Inline headers
#include "/cvmfs/juno.ihep.ac.cn/el9_amd64_gcc11/Release/J25.7.1/taosw/DataModel/ElecEvent/Event/CdElecEvt.h"

#undef  _BACKWARD_BACKWARD_WARNING_H
)DICTPAYLOAD";
    static const char* classesHeaders[] = {
"Tao::CdElecEvt", payloadCode, "@",
nullptr
};
    static bool isInitialized = false;
    if (!isInitialized) {
      TROOT::RegisterModule("CdElecEvtDict",
        headers, includePaths, payloadCode, fwdDeclCode,
        TriggerDictionaryInitialization_CdElecEvtDict_Impl, {}, classesHeaders, /*hasCxxModule*/false);
      isInitialized = true;
    }
  }
  static struct DictInit {
    DictInit() {
      TriggerDictionaryInitialization_CdElecEvtDict_Impl();
    }
  } __TheDictionaryInitializer;
}
void TriggerDictionaryInitialization_CdElecEvtDict() {
  TriggerDictionaryInitialization_CdElecEvtDict_Impl();
}
